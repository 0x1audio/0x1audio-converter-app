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
        if EXTENSIONS.get(path.suffix.lower()) == kind and (folder is None or Path(folder) == path.parent):
            # Already that format, right here: the song itself is the copy, so no "song 2.wav".
            made.append(ox.sound(path, title=path.stem))
            continue
        out = ox.audio.convert(
            path,
            kind,
            folder=folder or path.parent,
            on_progress=lambda fraction, i=i, label=label: ox.progress((i + fraction) / len(steps), label),
        )
        made.append(ox.sound(out, title=path.stem))
    return made
