# Audio Converter

An official Mixel app. Drop in songs and save each one in as many formats as you need, all at once.

- Writes WAV, AIFF, FLAC, MP3, AAC, Ogg Vorbis and Opus.
- Copies land next to the original, or in a folder you pick. Nothing is overwritten.
- Each copy is added to your Library.

The whole app is `app.py`: one `@ox.action`. Mixel draws its window from the action's signature.

## Develop

```sh
mixel check
mixel test
mixel dev     # opens it in Mixel and reloads it on save
```
