# Audio Converter

An official 0x1audio app. Drop in audio and save it in as many formats as you need, all at once.

- Reads anything ffmpeg reads, including the audio inside video files.
- Writes WAV, AIFF, FLAC, ALAC, WavPack, MP3, AAC, Ogg Vorbis, Opus, WMA, and AC3.
- Sample rate, channels, bit depth, and bitrate are optional. Formats that can't take a setting (Opus is always 48 kHz, MP3 tops out at 48 kHz and stereo) are adjusted for you.
- Tags carry over. Files land next to the original or in a folder you pick, and nothing is overwritten.

ffmpeg comes from the `imageio-ffmpeg` wheel, so there is nothing else to install.

## Develop

```sh
pnpm install
pnpm build
uv run --group dev python -m unittest discover tests
```

The page is `src/`, the worker is `converter.py`, and the conversion itself is `convert.py`.
