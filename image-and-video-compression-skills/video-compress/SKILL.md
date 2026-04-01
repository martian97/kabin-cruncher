---
name: video-compress
description: >
  Compress, shrink, optimize, or reduce video file size. Prepare videos for
  web, WordPress upload, or sharing. Handles MP4, MOV, AVI, MKV, WebM.
  Use for large video files, web-optimized encoding, resolution scaling,
  or codec conversion (H.264, H.265).
---

## Workflow

1. **Confirm inputs** with the user:
   - **Path**: file or folder to compress
   - **Target max size**: in MB (optional — if omitted, uses CRF mode for good quality/size balance)
   - **Output location**: default is `./compressed/` (relative to input)
   - **Max height**: optional resolution cap (e.g., 1080, 720)
   - **Codec**: `h264` (default, most compatible), `h265` (better compression), or `copy` (no re-encode)

2. **Ensure ffmpeg is available**: should be at `/opt/homebrew/bin/ffmpeg` (Homebrew)

3. **Run the compression script**:
   ```
   python .claude/skills/video-compress/scripts/compress.py <input_path> [options]
   ```

   Key options: `--max-size`, `--output`, `--max-height`, `--codec`, `--crf`, `--audio-bitrate`, `--dry-run`, `--recursive`

4. **Report summary** to the user: filename, original size, compressed size, reduction %, resolution, codec.

5. For compression strategy details, edge cases, and tuning guidance, see [reference/algorithm.md](reference/algorithm.md).
