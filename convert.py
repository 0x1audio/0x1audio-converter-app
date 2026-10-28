"""Convert audio between formats with ffmpeg."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from audio import Info, encoders, ffmpeg, free_path, probe


@dataclass(frozen=True)
class Format:
    id: str
    label: str
    ext: str
    encoder: str
    lossless: bool
    muxer: str
    depths: tuple[str, ...] = ()
    bitrates: tuple[int, ...] = ()
    rates: tuple[int, ...] = ()
    max_channels: int | None = None
    extra: tuple[str, ...] = ()

    def json(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "ext": self.ext,
            "lossless": self.lossless,
            "depths": list(self.depths),
            "bitrates": list(self.bitrates),
        }


_mp3_rates = (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000)

FORMATS: tuple[Format, ...] = (
    Format("wav", "WAV", "wav", "pcm_s24le", True, "wav", depths=("16", "24", "32", "32f")),
    Format("aiff", "AIFF", "aiff", "pcm_s24be", True, "aiff", depths=("16", "24", "32")),
    Format("flac", "FLAC", "flac", "flac", True, "flac", depths=("16", "24")),
    Format("alac", "ALAC", "m4a", "alac", True, "ipod", depths=("16", "24"), extra=("-movflags", "+faststart")),
    Format("wavpack", "WavPack", "wv", "wavpack", True, "wv", depths=("16", "24", "32f")),
    Format("mp3", "MP3", "mp3", "libmp3lame", False, "mp3", bitrates=(128, 160, 192, 256, 320), rates=_mp3_rates, max_channels=2, extra=("-id3v2_version", "3")),
    Format("aac", "AAC", "m4a", "aac", False, "ipod", bitrates=(96, 128, 160, 192, 256, 320), extra=("-movflags", "+faststart")),
    Format("ogg", "Ogg Vorbis", "ogg", "libvorbis", False, "ogg", bitrates=(96, 128, 160, 192, 256, 320)),
    Format("opus", "Opus", "opus", "libopus", False, "opus", bitrates=(64, 96, 128, 160, 192, 256), rates=(48000,), max_channels=2),
    Format("wma", "WMA", "wma", "wmav2", False, "asf", bitrates=(128, 160, 192, 256, 320), rates=_mp3_rates, max_channels=2),
    Format("ac3", "AC3", "ac3", "ac3", False, "ac3", bitrates=(192, 256, 384, 448, 640), rates=(32000, 44100, 48000)),
)

_by_id = {item.id: item for item in FORMATS}
_pcm = {
    "wav": {"16": "pcm_s16le", "24": "pcm_s24le", "32": "pcm_s32le", "32f": "pcm_f32le"},
    "aiff": {"16": "pcm_s16be", "24": "pcm_s24be", "32": "pcm_s32be"},
}


def available() -> list[Format]:
    have = encoders()
    return [item for item in FORMATS if item.id in _pcm or item.encoder in have]


def find(format_id: str) -> Format:
    found = _by_id.get(format_id)
    if found is None or found not in available():
        raise ValueError(f"{format_id} is not a format this computer can write.")
    return found


@dataclass
class Settings:
    rate: int | None = None
    channels: int | None = None
    depth: str = "24"
    bitrate: int = 320


@dataclass
class Plan:
    source: Info
    format: Format
    target: Path
    args: list[str] = field(default_factory=list)


def plan(source: Info, fmt: Format, folder: Path, settings: Settings, taken: set[Path] | None = None) -> Plan:
    target = free_path(folder / f"{Path(source.name).stem}.{fmt.ext}", avoid=Path(source.path))
    if taken is not None:
        while target in taken:
            target = free_path(target.with_name(f"{target.stem} (1){target.suffix}"), avoid=Path(source.path))
        taken.add(target)
    rate = _rate(fmt, settings.rate or source.rate)
    channels = settings.channels or source.channels
    if fmt.max_channels is not None:
        channels = min(channels, fmt.max_channels)
    args = [
        ffmpeg(), "-hide_banner", "-nostdin", "-y",
        "-i", source.path,
        "-map", "0:a:0", "-map_metadata", "0", "-vn", "-sn", "-dn",
    ]
    args += _codec(fmt, settings)
    args += ["-ar", str(rate), "-ac", str(channels)]
    args += list(fmt.extra)
    args += ["-f", fmt.muxer, "-progress", "pipe:1", "-nostats", str(target)]
    return Plan(source=source, format=fmt, target=target, args=args)


def _codec(fmt: Format, settings: Settings) -> list[str]:
    if fmt.id in _pcm:
        table = _pcm[fmt.id]
        return ["-c:a", table.get(settings.depth) or table["24"]]
    if fmt.lossless:
        depth = settings.depth if settings.depth in fmt.depths else "24"
        if fmt.id == "flac":
            return ["-c:a", "flac", "-sample_fmt", "s16" if depth == "16" else "s32", "-bits_per_raw_sample", "16" if depth == "16" else "24"]
        if fmt.id == "alac":
            return ["-c:a", "alac", "-sample_fmt", "s16p" if depth == "16" else "s32p"]
        if fmt.id == "wavpack":
            if depth == "32f":
                return ["-c:a", "wavpack", "-sample_fmt", "fltp"]
            return ["-c:a", "wavpack", "-sample_fmt", "s16p" if depth == "16" else "s32p", "-bits_per_raw_sample", depth]
    bitrate = min(fmt.bitrates, key=lambda value: (abs(value - settings.bitrate), -value))
    return ["-c:a", fmt.encoder, "-b:a", f"{bitrate}k"]


def _rate(fmt: Format, wanted: int) -> int:
    if not fmt.rates or wanted in fmt.rates:
        return wanted
    lower = [rate for rate in fmt.rates if rate <= wanted]
    return max(lower) if lower else min(fmt.rates)


class Cancelled(Exception):
    pass


def run(
    step: Plan,
    on_progress: Callable[[float], None] | None = None,
    cancel: threading.Event | None = None,
) -> Path:
    step.target.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    total = step.source.duration
    with subprocess.Popen(
        step.args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    ) as process:
        reader = threading.Thread(target=lambda: errors.extend(process.stderr or []), daemon=True)
        reader.start()
        for line in process.stdout or []:
            if cancel is not None and cancel.is_set():
                process.kill()
                break
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and total > 0 and on_progress:
                try:
                    on_progress(min(1.0, max(0.0, int(value) / 1_000_000 / total)))
                except ValueError:
                    pass
        process.wait()
        reader.join(timeout=5)
    if cancel is not None and cancel.is_set():
        step.target.unlink(missing_ok=True)
        raise Cancelled()
    if process.returncode != 0:
        step.target.unlink(missing_ok=True)
        tail = [line.strip() for line in errors if line.strip()][-3:]
        raise RuntimeError(" ".join(tail) or f"ffmpeg exited with {process.returncode}.")
    if on_progress:
        on_progress(1.0)
    return step.target


def convert(path: str, format_id: str, folder: str | None = None, settings: Settings | None = None) -> Path:
    source = probe(path)
    out = Path(folder) if folder else Path(source.path).parent
    return run(plan(source, find(format_id), out, settings or Settings()))
