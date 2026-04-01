import { NextRequest, NextResponse } from "next/server";
import path from "node:path";
import fs from "node:fs/promises";
import { spawn } from "node:child_process";
import os from "node:os";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const form = await req.formData();
    const file = form.get("file");

    if (!(file instanceof File)) {
      return new NextResponse("Missing file", { status: 400 });
    }

    const mode = String(form.get("mode") || "size");
    const targetPercentRaw = String(form.get("targetPercent") || "40");
    const crf = form.get("crf");
    const maxHeight = form.get("maxHeight");
    const codec = String(form.get("codec") || "h264");
    const audioBitrate = String(form.get("audioBitrate") || "128k");

    const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "vidc-"));
    const inputPath = path.join(tmpDir, file.name);

    const bytes = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(inputPath, bytes);

    const stat = await fs.stat(inputPath);
    const originalSizeBytes = stat.size;
    const targetPercent = Math.min(
      100,
      Math.max(5, Number.isNaN(Number(targetPercentRaw)) ? 40 : Number(targetPercentRaw))
    );
    const targetSizeBytes = Math.max(
      1,
      Math.floor((originalSizeBytes * targetPercent) / 100)
    );
    const maxSizeMb =
      targetSizeBytes > 0 ? targetSizeBytes / (1024 * 1024) : undefined;

    const outputDir = path.join(tmpDir, "compressed");

    const scriptPath = path.join(
      process.cwd(),
      "..",
      "image-and-video-compression-skills",
      "video-compress",
      "scripts",
      "compress.py"
    );

    const args: string[] = [scriptPath, inputPath, "--output", outputDir];

    if (mode === "size" && typeof maxSizeMb === "number") {
      args.push("--max-size", String(maxSizeMb));
    }

    if (mode === "crf" && crf) {
      args.push("--crf", String(crf));
    }

    if (maxHeight) {
      args.push("--max-height", String(maxHeight));
    }

    if (codec) {
      args.push("--codec", codec);
    }

    if (audioBitrate) {
      args.push("--audio-bitrate", audioBitrate);
    }

    const { stdout, stderr, code } = await runPython(args);

    if (code !== 0) {
      console.error("video-compress stderr:", stderr);
      return NextResponse.json(
        { error: "Video compression script failed", stderr },
        { status: 500 }
      );
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(stdout);
    } catch (err) {
      console.error("Failed to parse video-compress JSON:", err);
      return NextResponse.json(
        { error: "Could not parse compression result" },
        { status: 500 }
      );
    }

    const results = Array.isArray(parsed) ? parsed : [];
    let result = results[0] ?? null;

    if (result) {
      try {
        const outPath = path.join(outputDir, result.filename as string);
        const fileBuf = await fs.readFile(outPath);
        const mime = "video/mp4";
        const base64 = fileBuf.toString("base64");
        const url = `data:${mime};base64,${base64}`;
        result = { ...result, url };
      } catch (readErr) {
        console.error("Failed to read compressed video:", readErr);
      }
    }

    return NextResponse.json({ result });
  } catch (err) {
    console.error("compress-video error:", err);
    return new NextResponse("Unexpected error", { status: 500 });
  }
}

function runPython(args: string[]): Promise<{ stdout: string; stderr: string; code: number | null }> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", args, { env: process.env });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    proc.on("error", (err) => reject(err));
    proc.on("close", (code) => resolve({ stdout, stderr, code }));
  });
}

