---
name: image-compress
description: >
  Compress, resize, shrink, optimize, or reduce the file size of images and photos.
  Handles JPEG, PNG, WebP, and TIFF. Use for batch image processing, preparing
  images for web, email, or upload size limits, or when images are too large.
---

## Workflow

1. **Confirm inputs** with the user:
   - **Path**: folder or single file to compress
   - **Target max size**: in MB (default: 5)
   - **Output location**: default is `./compressed/` (relative to input)
   - **Preserve originals**: yes by default
   - **Max dimension**: optional cap on longest edge in pixels
   - **Output format**: `jpeg`, `webp`, or `keep` (default: `keep`)

2. **Ensure Pillow is installed**: `pip install Pillow`

3. **Run the compression script**:
   ```
   python .claude/skills/image-compress/scripts/compress.py <input_path> [options]
   ```

   Key options: `--max-size`, `--output`, `--max-dimension`, `--format`, `--quality-floor`, `--keep-exif`, `--dry-run`, `--recursive`

4. **Report summary** to the user: filename, original size, compressed size, reduction %, final dimensions.

5. For compression strategy details, edge cases, and tuning guidance, see [reference/algorithm.md](reference/algorithm.md).
