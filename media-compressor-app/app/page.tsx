"use client";

import { useState } from "react";

type ImageResult = {
  filename: string;
  original_size_mb: number;
  compressed_size_mb: number;
  reduction_pct: number;
  original_dimensions: string;
  final_dimensions: string;
  final_quality: number | string;
  url?: string;
};

type VideoResult = {
  filename: string;
  original_size_mb: number;
  compressed_size_mb: number | string;
  reduction_pct: number | string;
  resolution: string;
  codec: string;
  duration_sec: number;
  url?: string;
};

type Tab = "image" | "video";

type ImagePreset = "gentle" | "balanced" | "max";

export default function Page() {
  const [tab, setTab] = useState<Tab>("image");
  const [imageResult, setImageResult] = useState<ImageResult | null>(null);
  const [videoResult, setVideoResult] = useState<VideoResult | null>(null);

  return (
    <div className="shell">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div className="pill-label">
              <span className="pill-dot" />
              Kabin Cruncher
            </div>
            <h1 className="headline">
              HULK SMASH YOUR <span>FILES</span>
            </h1>
            <p className="lede">
              This crunchy boy will take your heavy files out back and… handle it. Drop anything in, Kabin Cruncher chews it down to shareable size and hands you back a fresh download.
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 10 }}>
            <div className="tabs" aria-label="Media type">
              <button
                className={"tab" + (tab === "image" ? " tab-active" : "")}
                type="button"
                onClick={() => setTab("image")}
              >
                Images
              </button>
              <button
                className={"tab" + (tab === "video" ? " tab-active" : "")}
                type="button"
                onClick={() => setTab("video")}
              >
                Videos
              </button>
            </div>
            <div className="tiny-label">Hosted on Railway · Crunch in the cloud</div>
          </div>
        </div>

        <div className="grid">
          {tab === "image" ? (
            <ImageCompressor onResult={setImageResult} />
          ) : (
            <VideoCompressor onResult={setVideoResult} />
          )}
          <PreviewPanel tab={tab} image={imageResult} video={videoResult} />
        </div>
      </div>
    </div>
  );
}

function ImageCompressor({ onResult }: { onResult: (r: ImageResult | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preset, setPreset] = useState<ImagePreset>("balanced");
  const [targetPercent, setTargetPercent] = useState("40");
  const [format, setFormat] = useState<"keep" | "jpeg" | "webp">("keep");
  const [keepExif, setKeepExif] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImageResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCompress() {
    if (!file) {
      setError("Choose an image first");
      return;
    }
    setError(null);
    setLoading(true);
      setResult(null);
      onResult(null);

    try {
      const form = new FormData();
      form.set("file", file);
      form.set("targetPercent", targetPercent || "50");
      form.set("format", format);
      const pct = Number(targetPercent) || 50;
      const autoQualityFloor =
        pct >= 80 ? 40 : pct >= 60 ? 32 : pct >= 40 ? 24 : pct >= 20 ? 18 : 12;
      form.set("qualityFloor", String(autoQualityFloor));
      form.set("keepExif", keepExif ? "1" : "0");

      const res = await fetch("/api/compress-image", {
        method: "POST",
        body: form
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Request failed");
      }

      const data = (await res.json()) as { result: ImageResult | null; error?: string };
      if (data.error) {
        throw new Error(data.error);
      }
      setResult(data.result);
      onResult(data.result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Compression failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">Image compression</div>
          <div className="tiny-label">JPG, PNG, WEBP, TIFF</div>
        </div>
        <span className="badge">
          <span className="badge-dot" />
          Pillow
        </span>
      </div>

      <div className="field-group">
        <div className="field">
          <label className="field-label">Source image</label>
          <label
            className="dropzone"
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f && f.type.startsWith("image/")) {
                setFile(f);
                setResult(null);
                setError(null);
              }
            }}
          >
            <input
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFile(f);
                  setResult(null);
                  setError(null);
                }
              }}
            />
            <div className="dropzone-label">
              {file ? file.name : "Drop an image or click to browse"}
            </div>
            <div className="dropzone-hint">
              Files are uploaded to Kabin Cruncher, crunched on the server, then ready to download.
            </div>
          </label>
        </div>

        <div className="field">
          <label className="field-label">Preset</label>
          <div className="pill-row">
            <button
              type="button"
              className="ghost-btn"
              style={
                preset === "gentle"
                  ? {
                      borderColor: "#FFE700",
                      color: "#ffffff",
                      background: "rgba(0,0,0,0.9)"
                    }
                  : undefined
              }
              onClick={() => {
                setPreset("gentle");
                setTargetPercent("75");
                setFormat("keep");
              }}
            >
              Gentle (share-ready)
            </button>
            <button
              type="button"
              className="ghost-btn"
              style={
                preset === "balanced"
                  ? {
                      borderColor: "#FFE700",
                      color: "#ffffff",
                      background: "rgba(0,0,0,0.9)"
                    }
                  : undefined
              }
              onClick={() => {
                setPreset("balanced");
                setTargetPercent("40");
                setFormat("keep");
              }}
            >
              Balanced
            </button>
            <button
              type="button"
              className="ghost-btn"
              style={
                preset === "max"
                  ? {
                      borderColor: "#FFE700",
                      color: "#ffffff",
                      background: "rgba(0,0,0,0.9)"
                    }
                  : undefined
              }
              onClick={() => {
                setPreset("max");
                setTargetPercent("10");
                setFormat("webp");
              }}
            >
              Max shrink (WEBP)
            </button>
          </div>
        </div>

        <div className="field">
          <label className="field-label">Target file size</label>
          <input
            className="input"
            type="range"
            min={5}
            max={90}
            step={5}
            value={targetPercent}
            onChange={(e) => setTargetPercent(e.target.value)}
          />
          <div className="field-hint">
            About <strong>{targetPercent}%</strong> of original file size; we keep dimensions and push quality as high as possible.
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
          <div className="field" style={{ flex: 1 }}>
            <label className="field-label">Format</label>
            <select
              className="select"
              value={format}
              onChange={(e) => setFormat(e.target.value as typeof format)}
            >
              <option value="keep">Keep (auto jpeg/webp)</option>
              <option value="jpeg">Force JPEG</option>
              <option value="webp">Force WebP</option>
            </select>
          </div>
          <div className="field" style={{ flex: 1, justifyContent: "flex-end" }}>
            <label className="field-label">EXIF metadata</label>
            <button
              type="button"
              className="ghost-btn"
              onClick={() => setKeepExif((v) => !v)}
            >
              {keepExif ? "Preserve EXIF" : "Strip EXIF"}
            </button>
          </div>
        </div>

        <div className="status-row">
          <div>
            <span className="status-strong">
              {result
                ? `${result.reduction_pct.toFixed(1)}% smaller`
                : "Ready to compress"}
            </span>
            {result && (
              <span style={{ marginLeft: 6 }}>
                · {result.original_dimensions} → {result.final_dimensions}
              </span>
            )}
          </div>
          <button
            type="button"
            className="primary-btn"
            onClick={handleCompress}
            disabled={loading || !file}
          >
            {loading ? "Crunching…" : "Compress image"}
          </button>
        </div>

        {result && (
          <ul className="summary-list">
            <li>
              <span className="summary-label">File size</span>
              <span className="summary-value">
                {result.original_size_mb.toFixed(2)} →{" "}
                {result.compressed_size_mb.toFixed(2)} MB
              </span>
            </li>
            <li>
              <span className="summary-label">Quality</span>
              <span className="summary-value">Q{String(result.final_quality)}</span>
            </li>
          </ul>
        )}

        {error && <div className="error">{error}</div>}
      </div>
    </section>
  );
}

function VideoCompressor({ onResult }: { onResult: (r: VideoResult | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"size" | "crf">("size");
  const [targetPercent, setTargetPercent] = useState("40");
  const [maxHeight, setMaxHeight] = useState("");
  const [codec, setCodec] = useState<"h264" | "h265" | "copy">("h264");
  const [crf, setCrf] = useState("23");
  const [audioBitrate, setAudioBitrate] = useState("128k");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VideoResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCompress() {
    if (!file) {
      setError("Choose a video first");
      return;
    }

    setError(null);
    setLoading(true);
    setResult(null);
    onResult(null);

    try {
      const form = new FormData();
      form.set("file", file);
      form.set("mode", mode);
      if (mode === "size") {
        form.set("targetPercent", targetPercent || "40");
      } else {
        form.set("crf", crf || "23");
      }
      if (maxHeight) form.set("maxHeight", maxHeight);
      form.set("codec", codec);
      form.set("audioBitrate", audioBitrate || "128k");

      const res = await fetch("/api/compress-video", {
        method: "POST",
        body: form
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Request failed");
      }

      const data = (await res.json()) as { result: VideoResult | null; error?: string };
      if (data.error) throw new Error(data.error);
      setResult(data.result);
      onResult(data.result);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Compression failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">Video compression</div>
          <div className="tiny-label">MP4, MOV, AVI, MKV, WEBM</div>
        </div>
        <span className="badge">
          <span className="badge-dot" />
          ffmpeg
        </span>
      </div>

      <div className="field-group">
        <div className="field">
          <label className="field-label">Source video</label>
          <label
            className="dropzone"
            onDragOver={(e) => {
              e.preventDefault();
            }}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f && f.type.startsWith("video/")) {
                setFile(f);
                setResult(null);
                setError(null);
              }
            }}
          >
            <input
              type="file"
              accept="video/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFile(f);
                  setResult(null);
                  setError(null);
                }
              }}
            />
            <div className="dropzone-label">
              {file ? file.name : "Drop a video or click to browse"}
            </div>
            <div className="dropzone-hint">
              Long clips are supported; Kabin Cruncher does the heavy lifting on the server.
            </div>
          </label>
        </div>

        <div className="field">
          <label className="field-label">Mode</label>
          <div className="pill-row">
            <button
              type="button"
              className={"ghost-btn"}
              style={
                mode === "size"
                  ? {
                      borderColor: "rgba(34,197,94,0.8)",
                      color: "#e5e7eb",
                      background: "rgba(15,23,42,0.95)"
                    }
                  : undefined
              }
              onClick={() => setMode("size")}
            >
              Target file size
            </button>
            <button
              type="button"
              className={"ghost-btn"}
              style={
                mode === "crf"
                  ? {
                      borderColor: "rgba(34,197,94,0.8)",
                      color: "#e5e7eb",
                      background: "rgba(15,23,42,0.95)"
                    }
                  : undefined
              }
              onClick={() => setMode("crf")}
            >
              CRF quality
            </button>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          {mode === "size" ? (
            <div className="field" style={{ flex: 1 }}>
              <label className="field-label">Target size</label>
              <input
                className="input"
                type="range"
                min={10}
                max={80}
                step={5}
                value={targetPercent}
                onChange={(e) => setTargetPercent(e.target.value)}
              />
              <div className="field-hint">
                About <strong>{targetPercent}%</strong> of original file size.
              </div>
            </div>
          ) : (
            <div className="field" style={{ flex: 1 }}>
              <label className="field-label">CRF</label>
              <input
                className="input"
                type="number"
                min={16}
                max={40}
                value={crf}
                onChange={(e) => setCrf(e.target.value)}
              />
            </div>
          )}
          <div className="field" style={{ flex: 1 }}>
            <label className="field-label">Max height</label>
            <input
              className="input"
              type="number"
              min={360}
              value={maxHeight}
              onChange={(e) => setMaxHeight(e.target.value)}
              placeholder="e.g. 1080"
            />
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <div className="field" style={{ flex: "1 1 220px" }}>
            <label className="field-label">Codec</label>
            <select
              className="select"
              value={codec}
              onChange={(e) => setCodec(e.target.value as typeof codec)}
            >
              <option value="h264">H.264 (max compatibility)</option>
              <option value="h265">H.265 / HEVC (smaller, may not play everywhere)</option>
              <option value="copy">Copy (remux only)</option>
            </select>
            {codec === "h265" && (
              <div className="field-hint">
                H.265 is smaller but may not play in all players (including some Macs and browsers). Use H.264 if a device can’t open the video.
              </div>
            )}
          </div>
          <div className="field" style={{ flex: "1 1 140px" }}>
            <label className="field-label">Audio bitrate</label>
            <input
              className="input"
              type="text"
              value={audioBitrate}
              onChange={(e) => setAudioBitrate(e.target.value)}
              placeholder="128k"
            />
          </div>
        </div>

        <div className="status-row">
          <div>
            <span className="status-strong">
              {result
                ? typeof result.reduction_pct === "number"
                  ? `${result.reduction_pct.toFixed(1)}% smaller`
                  : String(result.reduction_pct)
                : "Ready to compress"}
            </span>
            {result && (
              <span style={{ marginLeft: 6 }}>
                · {result.resolution} · {result.duration_sec.toFixed(1)}s
              </span>
            )}
          </div>
          <button
            type="button"
            className="primary-btn"
            onClick={handleCompress}
            disabled={loading || !file}
          >
            {loading ? "Encoding…" : "Compress video"}
          </button>
        </div>

        {result && (
          <ul className="summary-list">
            <li>
              <span className="summary-label">File size</span>
              <span className="summary-value">
                {result.original_size_mb.toFixed(2)} →{" "}
                {typeof result.compressed_size_mb === "number"
                  ? `${result.compressed_size_mb.toFixed(2)} MB`
                  : String(result.compressed_size_mb)}
              </span>
            </li>
            <li>
              <span className="summary-label">Codec</span>
              <span className="summary-value">{result.codec}</span>
            </li>
          </ul>
        )}

        {error && <div className="error">{error}</div>}
      </div>
    </section>
  );
}

function PreviewPanel({
  tab,
  image,
  video
}: {
  tab: Tab;
  image: ImageResult | null;
  video: VideoResult | null;
}) {
  const current = tab === "image" ? image : video;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">Preview</div>
          <div className="tiny-label">
            {current ? "Compressed output preview & download." : "Run a compression to see a preview."}
          </div>
        </div>
        <span className="preview-chip">
          {current ? (tab === "image" ? "Image" : "Video") : "Idle"}
        </span>
      </div>

      <div className="preview-shell">
        <div className="preview-header">
          <span>{tab === "image" ? "Image preview" : "Video preview"}</span>
          <span style={{ opacity: 0.6 }}>Processed in the Kabin Cruncher cloud</span>
        </div>
        {current && current.url ? (
          tab === "image" ? (
            <img
              src={current.url}
              alt={current.filename}
              className="preview-media"
              style={{ objectFit: "contain", maxHeight: 260 }}
            />
          ) : (
            <video
              className="preview-media"
              style={{ maxHeight: 260 }}
              controls
              src={current.url}
            />
          )
        ) : tab === "image" ? (
          <div
            className="preview-media"
            style={{
              height: 220,
              background:
                "repeating-conic-gradient(from 45deg, #020617 0 15deg, #020617 15deg 30deg) border-box"
            }}
          />
        ) : (
          <div
            className="preview-media"
            style={{
              height: 220,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#4b5563",
              fontSize: 12
            }}
          >
            ⏵ Encoded timeline
          </div>
        )}
        <div className="preview-filename">
          {current ? current.filename : "Drop a file and run a compression to see a downloadable asset."}
        </div>
        {current?.url && (
          <div style={{ marginTop: 10 }}>
            <a
              href={current.url}
              download={current.filename}
              className="primary-btn"
              style={{ textDecoration: "none", fontSize: 11, paddingInline: 12 }}
            >
              Download compressed {tab === "image" ? "image" : "video"}
            </a>
          </div>
        )}
      </div>
    </section>
  );
}

