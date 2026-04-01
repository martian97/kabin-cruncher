#!/usr/bin/env python3
"""Compress images to a target max file size while preserving quality.

Usage:
    compress.py <input_path> [options]

Options:
    --max-size FLOAT      Target max file size in MB (default: 5.0)
    --output DIR          Output directory (default: ./compressed)
    --max-dimension INT   Cap longest edge in pixels (only resize if specified or needed)
    --format FORMAT       jpeg, webp, or keep (default: keep)
    --quality-floor INT   Minimum quality before giving up (default: 20)
    --keep-exif           Preserve EXIF data (stripped by default)
    --dry-run             Report what would happen without writing
    --recursive           Process subdirectories

Requires: Pillow (pip install Pillow)
"""

import argparse
import io
import json
import os
import shutil
import sys

try:
    from PIL import Image
except ImportError:
    print(
        "Error: Pillow is required. Install it with: pip install Pillow",
        file=sys.stderr,
    )
    sys.exit(1)

# Suppress Pillow's DecompressionBombWarning for large images
Image.MAX_IMAGE_PIXELS = None

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif"}


def get_save_format(original_path, requested_format):
    """Determine the output format and extension."""
    ext = os.path.splitext(original_path)[1].lower()
    if requested_format == "jpeg":
        return "JPEG", ".jpg"
    elif requested_format == "webp":
        return "WEBP", ".webp"
    else:  # keep
        if ext in (".png", ".tiff", ".tif"):
            return "JPEG", ".jpg"
        elif ext in (".webp",):
            return "WEBP", ".webp"
        else:
            return "JPEG", ".jpg"


def estimate_size(img, fmt, quality, keep_exif, original_img=None):
    """Save image to memory buffer and return size in bytes."""
    buf = io.BytesIO()
    save_kwargs = {"format": fmt, "quality": quality}
    if fmt == "JPEG":
        save_kwargs["optimize"] = True
    if keep_exif and original_img is not None:
        exif = original_img.info.get("exif")
        if exif:
            save_kwargs["exif"] = exif
    img.save(buf, **save_kwargs)
    return buf.tell()


def compress_image(
    input_path,
    output_path,
    max_size_bytes,
    max_dimension,
    fmt,
    quality_floor,
    keep_exif,
    dry_run,
):
    """Compress a single image. Returns a result dict or None on failure."""
    original_size = os.path.getsize(input_path)
    original_size_mb = original_size / (1024 * 1024)

    # Already under target — just copy
    if original_size <= max_size_bytes:
        try:
            with Image.open(input_path) as img:
                dims = f"{img.size[0]}x{img.size[1]}"
        except Exception:
            dims = "unknown"
        if not dry_run:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(input_path, output_path)
        return {
            "filename": os.path.basename(input_path),
            "original_size_mb": round(original_size_mb, 2),
            "compressed_size_mb": round(original_size_mb, 2),
            "reduction_pct": 0.0,
            "original_dimensions": dims,
            "final_dimensions": dims,
            "final_quality": "original",
            "status": "copied (already under target)",
        }

    try:
        img = Image.open(input_path)
    except Exception as e:
        print(f"Warning: Cannot open {input_path}: {e}", file=sys.stderr)
        return None

    original_img = img.copy()
    original_dimensions = img.size  # (width, height)

    # Convert RGBA to RGB for JPEG
    if fmt == "JPEG" and img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = background

    # Apply max_dimension constraint if specified
    if max_dimension:
        w, h = img.size
        longest = max(w, h)
        if longest > max_dimension:
            scale = max_dimension / longest
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

    # Binary search for best quality
    current_img = img
    best_quality = None
    best_size = None

    while True:
        lo, hi = quality_floor, 95
        best_quality_this_round = lo
        best_size_this_round = None

        while lo <= hi:
            mid = (lo + hi) // 2
            size = estimate_size(current_img, fmt, mid, keep_exif, original_img)
            if size <= max_size_bytes:
                best_quality_this_round = mid
                best_size_this_round = size
                lo = mid + 1
            else:
                hi = mid - 1

        # Check if we found a valid quality
        if best_size_this_round is not None and best_size_this_round <= max_size_bytes:
            best_quality = best_quality_this_round
            best_size = best_size_this_round
            break

        # Check at quality floor
        size_at_floor = estimate_size(
            current_img, fmt, quality_floor, keep_exif, original_img
        )
        # If even the floor quality is above the requested target size,
        # keep the original dimensions and accept the closest achievable size.
        best_quality = quality_floor
        best_size = size_at_floor
        break

    final_dimensions = current_img.size
    compressed_size_mb = best_size / (1024 * 1024)
    reduction_pct = round((1 - best_size / original_size) * 100, 1)

    result = {
        "filename": os.path.basename(input_path),
        "original_size_mb": round(original_size_mb, 2),
        "compressed_size_mb": round(compressed_size_mb, 2),
        "reduction_pct": reduction_pct,
        "original_dimensions": f"{original_dimensions[0]}x{original_dimensions[1]}",
        "final_dimensions": f"{final_dimensions[0]}x{final_dimensions[1]}",
        "final_quality": best_quality,
    }

    if not dry_run:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        save_kwargs = {"format": fmt, "quality": best_quality, "optimize": True}
        if keep_exif:
            exif = original_img.info.get("exif")
            if exif:
                save_kwargs["exif"] = exif
        current_img.save(output_path, **save_kwargs)

    return result


def collect_images(input_path, recursive):
    """Collect image file paths from input path."""
    if os.path.isfile(input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return [input_path]
        else:
            print(f"Warning: {input_path} is not a supported image format", file=sys.stderr)
            return []

    if not os.path.isdir(input_path):
        print(f"Error: {input_path} does not exist", file=sys.stderr)
        sys.exit(1)

    images = []
    if recursive:
        for root, _, files in os.walk(input_path):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    images.append(os.path.join(root, f))
    else:
        for f in sorted(os.listdir(input_path)):
            full = os.path.join(input_path, f)
            if os.path.isfile(full):
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    images.append(full)
                else:
                    print(f"Warning: Skipping non-image file: {f}", file=sys.stderr)

    return images


def main():
    parser = argparse.ArgumentParser(
        description="Compress images to a target max file size"
    )
    parser.add_argument("input_path", help="File or directory to compress")
    parser.add_argument(
        "--max-size", type=float, default=5.0, help="Target max file size in MB (default: 5.0)"
    )
    parser.add_argument(
        "--output", default=None, help="Output directory (default: ./compressed)"
    )
    parser.add_argument(
        "--max-dimension", type=int, default=None, help="Cap longest edge in pixels"
    )
    parser.add_argument(
        "--format",
        choices=["jpeg", "webp", "keep"],
        default="keep",
        help="Output format (default: keep)",
    )
    parser.add_argument(
        "--quality-floor", type=int, default=20, help="Minimum quality (default: 20)"
    )
    parser.add_argument(
        "--keep-exif", action="store_true", help="Preserve EXIF data"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report without writing"
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Process subdirectories"
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

    max_size_bytes = int(args.max_size * 1024 * 1024)
    images = collect_images(input_path, args.recursive)

    if not images:
        print("No supported images found.", file=sys.stderr)
        sys.exit(1)

    results = []
    failures = 0

    for img_path in images:
        # Compute relative output path
        if os.path.isdir(input_path):
            rel = os.path.relpath(img_path, input_path)
        else:
            rel = os.path.basename(img_path)

        save_fmt, ext = get_save_format(img_path, args.format)
        out_name = os.path.splitext(rel)[0] + ext
        out_path = os.path.join(output_dir, out_name)

        result = compress_image(
            img_path,
            out_path,
            max_size_bytes,
            args.max_dimension,
            save_fmt,
            args.quality_floor,
            args.keep_exif,
            args.dry_run,
        )

        if result is None:
            failures += 1
        else:
            results.append(result)

    # Human-readable table to stderr
    if results:
        print(
            f"\n{'Filename':<40} {'Original':>10} {'Compressed':>12} {'Reduction':>10} {'Dimensions':>20} {'Quality':>8}",
            file=sys.stderr,
        )
        print("-" * 104, file=sys.stderr)
        for r in results:
            print(
                f"{r['filename']:<40} {r['original_size_mb']:>8.2f}MB {r['compressed_size_mb']:>10.2f}MB {r['reduction_pct']:>9.1f}% {str(r['final_dimensions']):>20} {str(r['final_quality']):>8}",
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
