#!/usr/bin/env python3
"""Compress videos to a target file size or quality level using ffmpeg.

Usage:
    compress.py <input_path> [options]

Options:
    --max-size FLOAT      Target max file size in MB (omit for CRF mode)
    --output DIR          Output directory (default: ./compressed)
    --max-height INT      Cap vertical resolution (e.g., 1080, 720)
    --codec CODEC         h264, h265, or copy (default: h264)
    --crf INT             Constant rate factor (default: 23 for h264, 28 for h265)
    --audio-bitrate STR   Audio bitrate (default: 128k)
    --dry-run             Report what would happen without encoding
    --recursive           Process subdirectories

Requires: ffmpeg and ffprobe in PATH or at /opt/homebrew/bin/
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

def _find_bin(name):
    """Find a binary in PATH, with Homebrew fallbacks for macOS."""
    found = shutil.which(name)
    if found:
        return found
    for prefix in ("/opt/homebrew/bin", "/usr/local/bin"):
        path = os.path.join(prefix, name)
        if os.path.isfile(path):
            return path
    return name  # let it fail with a clear error at runtime

FFMPEG = _find_bin("ffmpeg")
FFPROBE = _find_bin("ffprobe")

CRF_DEFAULTS = {"h264": 23, "h265": 28}
# Use encoders that are available in more FFmpeg builds.
# h264/hevc are native encoders; we already enable yuv420p + profile for compatibility.
CODEC_MAP = {"h264": "h264", "h265": "hevc"}


def probe(input_path):
    """Probe a video file and return metadata dict."""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def get_video_info(probe_data):
    """Extract relevant video info from probe data."""
    fmt = probe_data.get("format", {})
    duration = float(fmt.get("duration", 0))
    file_size = int(fmt.get("size", 0))

    video_stream = None
    audio_stream = None
    for stream in probe_data.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream

    width = int(video_stream["width"]) if video_stream else 0
    height = int(video_stream["height"]) if video_stream else 0
    video_codec = video_stream.get("codec_name", "unknown") if video_stream else None

    return {
        "duration": duration,
        "file_size": file_size,
        "width": width,
        "height": height,
        "video_codec": video_codec,
        "has_video": video_stream is not None,
        "has_audio": audio_stream is not None,
    }


def build_crf_command(input_path, output_path, codec, crf, max_height,
                      audio_bitrate, has_audio, current_height):
    """Build a single-pass CRF encoding command."""
    encoder = CODEC_MAP[codec]
    cmd = [FFMPEG, "-y", "-i", input_path]

    # Video filters
    vf = []
    if max_height and current_height > max_height:
        vf.append(f"scale=-2:{max_height}")

    video_opts = ["-c:v", encoder, "-crf", str(crf), "-preset", "medium"]
    # Improve compatibility with common players
    if codec == "h264":
        video_opts += ["-pix_fmt", "yuv420p", "-profile:v", "high"]
    else:
        video_opts += ["-pix_fmt", "yuv420p"]

    cmd += video_opts

    if vf:
        cmd += ["-vf", ",".join(vf)]

    if has_audio:
        cmd += ["-c:a", "aac", "-b:a", audio_bitrate]
    else:
        cmd += ["-an"]

    cmd += ["-movflags", "+faststart", output_path]
    return cmd


def build_two_pass_commands(input_path, output_path, codec, video_bitrate,
                            max_height, audio_bitrate, has_audio,
                            current_height, passlog):
    """Build two-pass encoding commands."""
    encoder = CODEC_MAP[codec]

    vf = []
    if max_height and current_height > max_height:
        vf.append(f"scale=-2:{max_height}")

    base = [FFMPEG, "-y", "-i", input_path]
    video_opts = ["-c:v", encoder, "-b:v", f"{video_bitrate}k", "-preset", "medium"]
    # Improve compatibility with common players
    if codec == "h264":
        video_opts += ["-pix_fmt", "yuv420p", "-profile:v", "high"]
    else:
        video_opts += ["-pix_fmt", "yuv420p"]

    if vf:
        video_opts += ["-vf", ",".join(vf)]

    # Pass 1
    pass1 = base + video_opts + [
        "-pass", "1", "-passlogfile", passlog, "-an", "-f", "null",
        "/dev/null"
    ]

    # Pass 2
    pass2 = base + video_opts + ["-pass", "2", "-passlogfile", passlog]

    if has_audio:
        pass2 += ["-c:a", "aac", "-b:a", audio_bitrate]
    else:
        pass2 += ["-an"]

    pass2 += ["-movflags", "+faststart", output_path]

    return pass1, pass2


def compress_video(input_path, output_path, max_size_mb, codec, crf,
                   max_height, audio_bitrate, dry_run):
    """Compress a single video. Returns a result dict or None on failure."""
    original_size = os.path.getsize(input_path)
    original_size_mb = original_size / (1024 * 1024)

    # Probe the input
    probe_data = probe(input_path)
    if probe_data is None:
        print(f"Warning: Cannot probe {input_path}", file=sys.stderr)
        return None

    info = get_video_info(probe_data)

    if not info["has_video"]:
        print(f"Warning: No video stream in {input_path}, skipping", file=sys.stderr)
        return None

    # Already under target size (if target specified)
    if max_size_mb and original_size_mb <= max_size_mb:
        if not dry_run:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(input_path, output_path)
        return {
            "filename": os.path.basename(input_path),
            "original_size_mb": round(original_size_mb, 2),
            "compressed_size_mb": round(original_size_mb, 2),
            "reduction_pct": 0.0,
            "resolution": f"{info['width']}x{info['height']}",
            "codec": info["video_codec"],
            "duration_sec": round(info["duration"], 1),
            "status": "copied (already under target)",
        }

    use_two_pass = (
        max_size_mb is not None
        and info["duration"] >= 1.0
        and codec != "copy"
    )

    if codec == "copy":
        # Stream copy — just remux
        cmd = [FFMPEG, "-y", "-i", input_path, "-c", "copy",
               "-movflags", "+faststart", output_path]
        if dry_run:
            return _dry_run_result(input_path, info, original_size_mb, codec)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: ffmpeg failed for {input_path}: {result.stderr[:200]}", file=sys.stderr)
            return None
    elif use_two_pass:
        # Calculate target video bitrate
        target_bytes = max_size_mb * 1024 * 1024
        audio_bps = _parse_bitrate(audio_bitrate)
        audio_total_bits = audio_bps * info["duration"] if info["has_audio"] else 0
        target_bits = target_bytes * 8
        video_bitrate_kbps = int((target_bits - audio_total_bits) / info["duration"] / 1000)

        if video_bitrate_kbps < 100:
            print(f"Warning: Calculated video bitrate ({video_bitrate_kbps}kbps) is very low for {input_path}. "
                  f"Consider a larger target size or lower resolution.", file=sys.stderr)

        if dry_run:
            return _dry_run_result(input_path, info, original_size_mb, codec,
                                   target_bitrate_kbps=video_bitrate_kbps)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        two_pass_failed = False
        with tempfile.TemporaryDirectory() as tmpdir:
            passlog = os.path.join(tmpdir, "passlog")
            pass1, pass2 = build_two_pass_commands(
                input_path, output_path, codec, video_bitrate_kbps,
                max_height, audio_bitrate, info["has_audio"],
                info["height"], passlog
            )
            print(f"  Pass 1/2: {os.path.basename(input_path)}...", file=sys.stderr)
            r1 = subprocess.run(pass1, capture_output=True, text=True)
            if r1.returncode != 0:
                print(f"Warning: Pass 1 failed for {input_path}: {r1.stderr}", file=sys.stderr)
                two_pass_failed = True
            else:
                print(f"  Pass 2/2: {os.path.basename(input_path)}...", file=sys.stderr)
                r2 = subprocess.run(pass2, capture_output=True, text=True)
                if r2.returncode != 0:
                    print(f"Warning: Pass 2 failed for {input_path}: {r2.stderr}", file=sys.stderr)
                    two_pass_failed = True

        if two_pass_failed:
            # Fallback: run a single-pass CRF encode instead of failing outright
            print(f"  Falling back to CRF encode for {os.path.basename(input_path)}", file=sys.stderr)
            cmd = build_crf_command(
                input_path, output_path, codec, crf, max_height,
                audio_bitrate, info["has_audio"], info["height"]
            )
            print(f"  Encoding (fallback CRF {crf}): {os.path.basename(input_path)}", file=sys.stderr)
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"Warning: ffmpeg failed for {input_path}: {r.stderr}", file=sys.stderr)
                return None
    else:
        # CRF mode
        if dry_run:
            return _dry_run_result(input_path, info, original_size_mb, codec, crf=crf)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = build_crf_command(
            input_path, output_path, codec, crf, max_height,
            audio_bitrate, info["has_audio"], info["height"]
        )
        print(f"  Encoding: {os.path.basename(input_path)} (CRF {crf})...", file=sys.stderr)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"Warning: ffmpeg failed for {input_path}: {r.stderr}", file=sys.stderr)
            return None

    # Read output size
    compressed_size = os.path.getsize(output_path)
    compressed_size_mb = compressed_size / (1024 * 1024)
    reduction_pct = round((1 - compressed_size / original_size) * 100, 1)

    # Probe output for final resolution
    out_probe = probe(output_path)
    out_info = get_video_info(out_probe) if out_probe else info
    final_res = f"{out_info['width']}x{out_info['height']}"

    return {
        "filename": os.path.basename(input_path),
        "original_size_mb": round(original_size_mb, 2),
        "compressed_size_mb": round(compressed_size_mb, 2),
        "reduction_pct": reduction_pct,
        "resolution": final_res,
        "codec": codec,
        "duration_sec": round(info["duration"], 1),
        "status": "compressed",
    }


def _dry_run_result(input_path, info, original_size_mb, codec, crf=None,
                    target_bitrate_kbps=None):
    """Build a dry-run result dict."""
    result = {
        "filename": os.path.basename(input_path),
        "original_size_mb": round(original_size_mb, 2),
        "compressed_size_mb": "N/A (dry run)",
        "reduction_pct": "N/A",
        "resolution": f"{info['width']}x{info['height']}",
        "codec": codec,
        "duration_sec": round(info["duration"], 1),
        "status": "dry run",
    }
    if crf is not None:
        result["crf"] = crf
    if target_bitrate_kbps is not None:
        result["target_bitrate_kbps"] = target_bitrate_kbps
    return result


def _parse_bitrate(bitrate_str):
    """Parse a bitrate string like '128k' to bits per second."""
    s = bitrate_str.strip().lower()
    if s.endswith("k"):
        return int(s[:-1]) * 1000
    elif s.endswith("m"):
        return int(s[:-1]) * 1000000
    return int(s)


def collect_videos(input_path, recursive):
    """Collect video file paths from input path."""
    if os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [input_path]
        else:
            print(f"Warning: {input_path} is not a supported video format", file=sys.stderr)
            return []

    if not os.path.isdir(input_path):
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    videos = []
    if recursive:
        for root, _, files in os.walk(input_path):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    videos.append(os.path.join(root, f))
    else:
        for f in sorted(os.listdir(input_path)):
            full = os.path.join(input_path, f)
            if os.path.isfile(full):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    videos.append(full)

    return videos


def main():
    parser = argparse.ArgumentParser(
        description="Compress videos using ffmpeg"
    )
    parser.add_argument("input_path", help="File or directory to compress")
    parser.add_argument(
        "--max-size", type=float, default=None,
        help="Target max file size in MB (omit for CRF mode)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output directory (default: ./compressed)"
    )
    parser.add_argument(
        "--max-height", type=int, default=None,
        help="Cap vertical resolution (e.g., 1080, 720)"
    )
    parser.add_argument(
        "--codec", choices=["h264", "h265", "copy"], default="h264",
        help="Video codec (default: h264)"
    )
    parser.add_argument(
        "--crf", type=int, default=None,
        help="Constant rate factor (default: 23 for h264, 28 for h265)"
    )
    parser.add_argument(
        "--audio-bitrate", default="128k",
        help="Audio bitrate (default: 128k)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report without encoding"
    )
    parser.add_argument(
        "--recursive", action="store_true",
        help="Process subdirectories"
    )
    args = parser.parse_args()

    input_path = os.path.abspath(args.input_path)

    # Determine output directory
    if args.output:
        output_dir = os.path.abspath(args.output)
    elif os.path.isdir(input_path):
        output_dir = os.path.join(input_path, "compressed")
    else:
        output_dir = os.path.join(os.path.dirname(input_path), "compressed")

    # Resolve CRF default
    codec = args.codec
    if args.crf is not None:
        crf = args.crf
    else:
        crf = CRF_DEFAULTS.get(codec, 23)

    # Check ffmpeg
    if not os.path.isfile(FFMPEG):
        print(f"Error: ffmpeg not found at {FFMPEG}", file=sys.stderr)
        print("Install with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    videos = collect_videos(input_path, args.recursive)

    if not videos:
        print("No supported video files found.", file=sys.stderr)
        sys.exit(1)

    results = []
    failures = 0

    for vid_path in videos:
        # Compute relative output path
        if os.path.isdir(input_path):
            rel = os.path.relpath(vid_path, input_path)
        else:
            rel = os.path.basename(vid_path)

        # Output is always .mp4 unless codec is copy
        if codec == "copy":
            out_name = rel
        else:
            out_name = os.path.splitext(rel)[0] + ".mp4"
        out_path = os.path.join(output_dir, out_name)

        result = compress_video(
            vid_path, out_path, args.max_size, codec, crf,
            args.max_height, args.audio_bitrate, args.dry_run
        )

        if result is None:
            failures += 1
        else:
            results.append(result)

    # Human-readable table to stderr
    if results:
        print(
            f"\n{'Filename':<40} {'Original':>10} {'Compressed':>12} {'Reduction':>10} {'Resolution':>14} {'Codec':>8} {'Duration':>10}",
            file=sys.stderr,
        )
        print("-" * 108, file=sys.stderr)
        for r in results:
            compressed = (f"{r['compressed_size_mb']:>10.2f}MB"
                          if isinstance(r["compressed_size_mb"], (int, float))
                          else f"{r['compressed_size_mb']:>12}")
            reduction = (f"{r['reduction_pct']:>9.1f}%"
                         if isinstance(r["reduction_pct"], (int, float))
                         else f"{r['reduction_pct']:>10}")
            print(
                f"{r['filename']:<40} {r['original_size_mb']:>8.2f}MB {compressed} {reduction} {r['resolution']:>14} {r['codec']:>8} {r['duration_sec']:>8.1f}s",
                file=sys.stderr,
            )
        print(file=sys.stderr)

    if args.dry_run:
        print("[DRY RUN] No files were written.", file=sys.stderr)

    # JSON summary to stdout
    print(json.dumps(results, indent=2))

    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    main()
