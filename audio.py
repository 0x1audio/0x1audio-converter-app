"""Read audio files with the ffmpeg that ships in the imageio-ffmpeg wheel."""

from __future__ import annotations

import functools
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

_duration = re.compile(r"Duration: (\d+):(\d{2}):(\d{2}(?:\.\d+)?)")
_stream = re.compile(r"Stream #\d+:\d+[^:]*: Audio: ([^,\n]+), (\d+) Hz, ([^,\n]+)(?:, ([^,\n]+))?(?:, (\d+) kb/s)?")
_layouts = {"mono": 1, "stereo": 2, "2.1": 3, "3.0": 3, "quad": 4, "4.0": 4, "5.0": 5, "5.1": 6, "6.1": 7, "7.1": 8}


@dataclass(frozen=True)
class Info:
    path: str
    name: str
    codec: str
    rate: int
    channels: int
    duration: float
    bitrate: int | None

    def json(self) -> dict:
        return {
            "path": self.path,
            "name": self.name,
            "codec": self.codec,
            "rate": self.rate,
            "channels": self.channels,
            "duration": self.duration,
            "bitrate": self.bitrate,
        }


@functools.cache
def ffmpeg() -> str:
    import imageio_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    mode = os.stat(exe).st_mode
    if not mode & stat.S_IXUSR:
        os.chmod(exe, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


@functools.cache
def encoders() -> frozenset[str]:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30).stdout
    found = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("A"):
            found.add(parts[1])
    return frozenset(found)


def probe(path: str) -> Info:
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"{source.name} is not there anymore.")
    result = subprocess.run(
        [ffmpeg(), "-hide_banner", "-nostdin", "-i", str(source)],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
    )
    text = result.stderr
    stream = _stream.search(text)
    if not stream:
        raise ValueError(f"{source.name} has no audio ffmpeg can read.")
    codec = stream.group(1).split(" ")[0]
    duration = 0.0
    found = _duration.search(text)
    if found:
        hours, minutes, seconds = found.groups()
        duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    bitrate = int(stream.group(5)) if stream.group(5) else None
    return Info(
        path=str(source),
        name=source.name,
        codec=codec,
        rate=int(stream.group(2)),
        channels=channel_count(stream.group(3)),
        duration=duration,
        bitrate=bitrate,
    )


def channel_count(layout: str) -> int:
    layout = layout.strip()
    counted = re.match(r"(\d+) channels", layout)
    if counted:
        return int(counted.group(1))
    base = layout.split("(")[0]
    return _layouts.get(base, 2)


def free_path(target: Path, avoid: Path | None = None) -> Path:
    candidate = target
    index = 1
    while candidate.exists() or (avoid is not None and candidate.resolve() == avoid.resolve()):
        candidate = target.with_name(f"{target.stem} ({index}){target.suffix}")
        index += 1
    return candidate
