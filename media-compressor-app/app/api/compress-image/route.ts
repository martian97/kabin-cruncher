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

    const targetPercentRaw = String(form.get("targetPercent") || "50");
    const targetPercent = Math.min(
      100,
      Math.max(5, Number.isNaN(Number(targetPercentRaw)) ? 50 : Number(targetPercentRaw))
    );
    const format = String(form.get("format") || "keep");
    const qualityFloor = parseInt(String(form.get("qualityFloor") || "25"), 10);
    const keepExif = String(form.get("keepExif") || "0") === "1";

    const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "imgc-"));
    const inputPath = path.join(tmpDir, file.name);

    const bytes = Buffer.from(await file.arrayBuffer());
    await fs.writeFile(inputPath, bytes);

    const stat = await fs.stat(inputPath);
    const originalSizeBytes = stat.size;
    const targetSizeBytes = Math.max(
      1,
      Math.floor((originalSizeBytes * targetPercent) / 100)
    );
    const maxSizeMb = targetSizeBytes / (1024 * 1024);

    const outputDir = path.join(tmpDir, "compressed");

    const scriptPath = path.join(
      process.cwd(),
      "..",
      "image-and-video-compression-skills",
      "image-compress",
      "scripts",
      "compress.py"
    );

    const args = [
      scriptPath,
      inputPath,
      "--max-size",
      String(maxSizeMb),
      "--output",
      outputDir,
      "--quality-floor",
      String(qualityFloor)
    ];

    if (format === "jpeg" || format === "webp" || format === "keep") {
      args.push("--format", format);
    }

    if (keepExif) {
      args.push("--keep-exif");
    }

    const { stdout, stderr, code } = await runPython(args);

    if (code !== 0) {
      console.error("image-compress stderr:", stderr);
      return NextResponse.json(
        { error: "Image compression script failed", stderr },
        { status: 500 }
      );
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(stdout);
    } catch (err) {
      console.error("Failed to parse image-compress JSON:", err);
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
        const ext = path.extname(outPath).toLowerCase();
        const mime =
          ext === ".png"
            ? "image/png"
            : ext === ".webp"
            ? "image/webp"
            : "image/jpeg";
        const base64 = fileBuf.toString("base64");
        const url = `data:${mime};base64,${base64}`;
        result = { ...result, url };
      } catch (readErr) {
        console.error("Failed to read compressed image:", readErr);
      }
    }

    return NextResponse.json({ result });
  } catch (err) {
    console.error("compress-image error:", err);
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

