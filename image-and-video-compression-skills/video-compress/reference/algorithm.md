# Video Compression Algorithm Reference

## Mode 1: CRF (Constant Rate Factor) — Default

Used when no `--max-size` is specified. Produces good quality at a reasonable file size.

- **H.264**: CRF 23 (default), range 0-51, lower = better quality / larger file
- **H.265**: CRF 28 (default), range 0-51, same scale but better compression per CRF point
- Single-pass encoding, fast and simple
- Preset: `medium` (good speed/quality trade-off)

## Mode 2: Two-Pass Target Size

Used when `--max-size` is specified. Calculates a target bitrate to hit the desired file size.

### Bitrate Calculation

```
audio_bitrate = 128000  # bits/sec (default)
target_bits = target_size_bytes * 8
video_bitrate = (target_bits - audio_bitrate * duration) / duration
```

If the calculated video bitrate is unreasonably low (< 100kbps), warn the user.

### Two-Pass Encoding

1. **Pass 1**: Analyze video, write stats to temp file (output to /dev/null)
2. **Pass 2**: Encode using stats from pass 1 for optimal bitrate distribution

Two-pass produces more consistent quality than single-pass when targeting a file size.

## Resolution Scaling

- Use `-vf scale=-2:{height}` to cap vertical resolution (e.g., 720, 1080)
- The `-2` ensures width stays even (required by H.264/H.265 encoders)
- Only downscale — if video is already at or below the target height, skip scaling

## Audio

- Re-encode to AAC at 128kbps by default
- Customizable via `--audio-bitrate`
- If input has no audio stream, skip audio encoding

## Codec Selection

- **H.264** (`libx264`): Most compatible. Works everywhere. Default choice.
- **H.265** (`libx265`): ~30-50% better compression at same quality. Good browser support now.
- **Copy**: Stream copy, no re-encoding. Only useful for container changes or when input is already optimal.

## Output Container

- Always `.mp4` for H.264/H.265 output (web-compatible, faststart enabled)
- Use `-movflags +faststart` for web playback (moves moov atom to start of file)

## Edge Cases

- **Already under target size**: copy to output unchanged (stream copy, no re-encoding)
- **Non-video files**: skip with warning
- **Audio-only files**: skip with warning (no video stream detected)
- **Very short videos** (< 1 second): use CRF mode even if max-size specified (two-pass unreliable)
- **Permission errors**: warn to stderr, skip, continue processing
- **Corrupt/unreadable files**: warn to stderr, skip, continue processing

## Learnings

_(No issues discovered yet.)_
