"""Audio Converter worker. The page probes files, starts a job, and polls it."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from ox1audio import serve

from audio import probe
from convert import Cancelled, Settings, available, find, plan, run

_jobs: dict[str, dict] = {}
_cancels: dict[str, threading.Event] = {}
_lock = threading.Lock()
_seq = 0


def formats(call):
    return {"formats": [item.json() for item in available()]}


def inspect(call):
    body = call.body if isinstance(call.body, dict) else {}
    files = body.get("files")
    if not isinstance(files, list):
        raise ValueError("Choose an audio file.")
    found = []
    for path in files:
        if not isinstance(path, str) or not path:
            continue
        try:
            found.append({"ok": True, **probe(path).json()})
        except Exception as exc:
            found.append({"ok": False, "path": path, "name": Path(path).name, "error": str(exc)})
    return {"files": found}


def start(call):
    body = call.body if isinstance(call.body, dict) else {}
    files = [item for item in body.get("files") or [] if isinstance(item, str) and item]
    if not files:
        raise ValueError("Choose an audio file.")
    targets = [find(item) for item in body.get("formats") or [] if isinstance(item, str)]
    if not targets:
        raise ValueError("Choose at least one format.")
    output = body.get("output") if isinstance(body.get("output"), str) and body.get("output") else None
    settings = Settings(
        rate=_positive(body.get("rate")),
        channels=_positive(body.get("channels")),
        depth=str(body.get("depth") or "24"),
        bitrate=_positive(body.get("bitrate")) or 320,
    )
    job = _reserve(len(files) * len(targets))
    threading.Thread(target=_run, args=(job, files, targets, output, settings), daemon=True).start()
    return {"id": job}


def status(call):
    body = call.body if isinstance(call.body, dict) else {}
    job = body.get("id")
    with _lock:
        found = _jobs.get(job) if isinstance(job, str) else None
        if found is None:
            raise ValueError("That conversion is not running.")
        return {key: value for key, value in found.items() if key != "process"}


def cancel(call):
    body = call.body if isinstance(call.body, dict) else {}
    job = body.get("id")
    event = _cancels.get(job) if isinstance(job, str) else None
    if event is not None:
        event.set()
    return {"ok": True}


def _reserve(total: int) -> str:
    global _seq
    with _lock:
        _seq += 1
        job = str(_seq)
        _jobs[job] = {
            "progress": 0.0,
            "total": total,
            "finished": 0,
            "current": "",
            "done": False,
            "cancelled": False,
            "error": None,
            "outputs": [],
            "failures": [],
            "elapsed": 0.0,
        }
        _cancels[job] = threading.Event()
        while len(_jobs) > 8:
            oldest = next(iter(_jobs))
            _jobs.pop(oldest, None)
            _cancels.pop(oldest, None)
        return job


def _update(job: str, **fields) -> None:
    with _lock:
        current = _jobs.get(job)
        if current is not None:
            current.update(fields)


def _run(job: str, files: list[str], targets, output: str | None, settings: Settings) -> None:
    started = time.perf_counter()
    cancel_event = _cancels[job]
    total = len(files) * len(targets)
    index = 0
    outputs: list[dict] = []
    failures: list[dict] = []
    taken: set[Path] = set()
    for path in files:
        try:
            source = probe(path)
        except Exception as exc:
            failures.append({"path": path, "format": None, "error": str(exc)})
            index += len(targets)
            continue
        folder = Path(output) if output else Path(source.path).parent
        for fmt in targets:
            if cancel_event.is_set():
                break
            _update(job, current=f"{source.name} → {fmt.label}", progress=index / total)

            def progress(fraction: float, base=index) -> None:
                _update(job, progress=(base + fraction) / total)

            try:
                step = plan(source, fmt, folder, settings, taken)
                written = run(step, progress, cancel_event)
                outputs.append({"path": str(written), "name": written.name, "format": fmt.label, "source": source.name})
            except Cancelled:
                break
            except Exception as exc:
                failures.append({"path": path, "format": fmt.label, "error": str(exc)})
            index += 1
            _update(job, finished=index, outputs=list(outputs), failures=list(failures))
        if cancel_event.is_set():
            break
    cancelled = cancel_event.is_set()
    _update(
        job,
        done=True,
        cancelled=cancelled,
        progress=1.0 if not cancelled else index / total,
        current="",
        outputs=outputs,
        failures=failures,
        error=None if outputs or not failures else failures[0]["error"],
        elapsed=round(time.perf_counter() - started, 2),
    )


def _positive(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    if isinstance(value, str) and value.isdigit() and int(value) > 0:
        return int(value)
    return None


if __name__ == "__main__":
    serve({"formats": formats, "inspect": inspect, "start": start, "status": status, "cancel": cancel})
