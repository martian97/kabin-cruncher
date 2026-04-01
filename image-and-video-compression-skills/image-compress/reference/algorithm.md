# Image Compression Algorithm Reference

## Core Strategy: Binary Search on Quality

1. Start at quality 95
2. Binary search for the highest JPEG/WebP quality that produces a file <= target size
3. Each test save uses `io.BytesIO` (no intermediate disk writes)
4. Quality range: user-specified floor (default 20) to 95

## Fallback: Progressive Dimension Reduction

If the quality floor is reached and the file still exceeds the target size:
1. Scale dimensions down by 10%
2. Retry the binary search at the new dimensions
3. Repeat until target is met or image becomes unreasonably small (< 100px on longest edge)

## Resampling

- Use `Image.LANCZOS` for all dimension reductions (best quality for downscaling)

## EXIF Handling

- Strip EXIF data by default (camera photos often carry 1-2MB of metadata)
- `--keep-exif` flag preserves it when needed

## Format Conversion

- `keep` mode: PNGs and TIFFs are converted to JPEG (since lossless formats can't be quality-compressed effectively). JPEGs and WebPs stay as-is.
- `jpeg` / `webp` modes: force output to the specified format

## Edge Cases

- **Already under target**: copy to output unchanged (no re-encoding)
- **Non-image files in directory**: warn to stderr, skip, continue processing
- **Permission errors**: warn to stderr, skip, continue processing
- **Corrupt/unreadable images**: warn to stderr, skip, continue processing
- **RGBA images to JPEG**: convert to RGB first (JPEG doesn't support alpha)

## Learnings

_(No issues discovered yet.)_
