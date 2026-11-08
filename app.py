import ox1audio as ox

FORMATS = {"wav": "WAV", "aiff": "AIFF", "flac": "FLAC", "mp3": "MP3", "aac": "AAC", "ogg": "Ogg", "opus": "Opus"}


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
        out = ox.audio.convert(
            path,
            kind,
            folder=folder or path.parent,
            on_progress=lambda fraction, i=i, label=label: ox.progress((i + fraction) / len(steps), label),
        )
        made.append(ox.sound(out, title=path.stem))
    return made
