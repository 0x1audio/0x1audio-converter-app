import ox1audio as ox
from pathlib import Path


@ox.screen("Audio Converter")
def convert(files: ox.Files, format: ox.Choice("wav", "aiff", "flac", "mp3", "aac", "ogg", "opus")):
    paths = files if isinstance(files, list) else []
    total = max(len(paths), 1)
    for index, audio in enumerate(paths):
        source = Path(str(audio))
        yield ox.progress(index / total, source.stem)
        out = ox.audio.convert(str(source), str(format))
        yield ox.sound(out, title=source.stem)
    yield ox.progress(1, "Done")


if __name__ == "__main__":
    ox.run()
