from pathlib import Path

import ox1audio as ox

FORMATS = {"wav": "WAV", "aiff": "AIFF", "flac": "FLAC", "mp3": "MP3", "aac": "AAC", "ogg": "Ogg", "opus": "Opus"}
# The format a file already is, by its extension.
EXTENSIONS = {".wav": "wav", ".wave": "wav", ".aif": "aiff", ".aiff": "aiff", ".flac": "flac", ".mp3": "mp3", ".m4a": "aac", ".aac": "aac", ".ogg": "ogg", ".opus": "opus"}


@ox.action("Convert")
def convert(
    files: ox.Files("audio"),
    formats: ox.Choice(*FORMATS, multiple=True),
    folder: ox.Folder(label="Save to") | None = None,
):
    steps = [(path, kind) for path in files for kind in formats]
    made = []
    for i, (path, kind) in enumerate(steps):
        label = f"{path.name} to {FORMATS[kind]}"
        ox.progress(i / len(steps), label)
        # Next to the song, unless it came from Open with (read-only): then the copy goes to the Library.
        target = folder or ox.beside(path)
        if EXTENSIONS.get(path.suffix.lower()) == kind:
            if target is None:
                continue  # From Open with, already this format: it's in the Library as it is.
            if Path(target) == path.parent:
                # Already that format, right here: the song itself is the copy, so no "song 2.wav".
                # Its title says so, so nobody thinks it was converted or written over (GAB-152).
                made.append(ox.sound(path, title=f"{path.stem} (already {FORMATS[kind]})", duration=_length(path)))
                continue
        out = ox.audio.convert(
            path,
            kind,
            folder=target,
            on_progress=lambda fraction, i=i, label=label: ox.progress((i + fraction) / len(steps), label),
        )
        # The length comes with the copy, so the result row shows it before the Library has measured it.
        made.append(ox.sound(out, title=path.stem, duration=_length(out)))
    if not made:
        raise ox.Problem("Your Library already has this in that format.", hint="Choose another format.")
    return made


def _length(path) -> float | None:
    try:
        return round(ox.audio.probe(path).duration, 3) or None
    except Exception:
        return None
