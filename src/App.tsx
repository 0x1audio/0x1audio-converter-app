import { useEffect, useState } from "react"
import { CheckCircleIcon, FileAudioIcon, FolderOpenIcon, UploadSimpleIcon, WarningCircleIcon, XIcon } from "@phosphor-icons/react"
import { Badge, Button, Label, Progress } from "@0x1audio/design-system"
import { host } from "@0x1audio/sdk/page"

import { basename, channels, duration, rate, useDrop } from "./drop.ts"
import { fallback, type Format } from "./formats.ts"

interface Source {
  path: string
  name: string
  ok: boolean
  codec?: string
  rate?: number
  channels?: number
  duration?: number
  bitrate?: number | null
  error?: string
}

interface Output {
  path: string
  name: string
  format: string
  source: string
}

interface Job {
  progress: number
  total: number
  finished: number
  current: string
  done: boolean
  cancelled: boolean
  error: string | null
  outputs: Output[]
  failures: Array<{ path: string; format: string | null; error: string }>
  elapsed: number
}

export function App() {
  const [formats, setFormats] = useState<Format[]>(fallback)
  const [files, setFiles] = useState<Source[]>([])
  const [chosen, setChosen] = useState<string[]>(["mp3"])
  const [output, setOutput] = useState("")
  const [job, setJob] = useState<{ id: string; state: Job } | null>(null)
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState("")

  const dragging = useDrop((paths) => void add(paths), setMessage)

  useEffect(() => {
    const bridge = host()
    if (!bridge) return
    void bridge
      .call<{ formats: Format[] }>("formats")
      .then((result) => {
        setFormats(result.formats)
        setChosen((current) => current.filter((id) => result.formats.some((item) => item.id === id)))
      })
      .catch(() => {})
  }, [])

  async function add(paths: string[]) {
    const bridge = host()
    const fresh = paths.filter((path) => !files.some((item) => item.path === path))
    if (!fresh.length) return
    setMessage("")
    if (!bridge) {
      setFiles((current) => [...current, ...fresh.map((path) => ({ path, name: basename(path), ok: true }))])
      return
    }
    try {
      const result = await bridge.call<{ files: Source[] }>("inspect", { files: fresh })
      setFiles((current) => {
        const known = new Set(current.map((item) => item.path))
        return [...current, ...result.files.filter((item) => !known.has(item.path))]
      })
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not read those files.")
    }
  }

  async function chooseFiles() {
    const bridge = host()
    if (!bridge?.pick) {
      setMessage("Open this app in 0x1audio.")
      return
    }
    const picked = await bridge.pick("file")
    if (picked.length) await add(picked)
  }

  async function chooseFolder() {
    const bridge = host()
    if (!bridge?.pick) {
      setMessage("Open this app in 0x1audio.")
      return
    }
    const picked = await bridge.pick("folder")
    if (picked[0]) setOutput(picked[0])
  }

  function toggle(id: string) {
    setChosen((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  async function convert() {
    const bridge = host()
    if (!bridge) {
      setMessage("Open this app in 0x1audio.")
      return
    }
    const ready = files.filter((item) => item.ok)
    if (!ready.length) {
      setMessage("Add audio to convert.")
      return
    }
    if (!chosen.length) {
      setMessage("Choose at least one format.")
      return
    }
    setPending(true)
    setMessage("")
    try {
      const created = await bridge.call<{ id: string }>("start", {
        files: ready.map((item) => item.path),
        formats: chosen,
        output,
      })
      for (;;) {
        const state = await bridge.call<Job>("status", { id: created.id })
        setJob({ id: created.id, state })
        if (state.done) {
          if (state.cancelled) setMessage("Stopped.")
          else if (state.error) setMessage(state.error)
          break
        }
        await new Promise((resolve) => setTimeout(resolve, 300))
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong.")
    } finally {
      setPending(false)
    }
  }

  function stop() {
    if (job) void host()?.call("cancel", { id: job.id })
  }

  const ready = files.filter((item) => item.ok).length
  const lossless = formats.filter((item) => item.lossless)
  const lossy = formats.filter((item) => !item.lossless)
  const state = job?.state
  const count = ready * chosen.length

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-6 py-10 text-foreground">
      <header className="flex flex-col gap-2">
        <h1 className="text-xl font-medium">Audio Converter</h1>
        <p className="text-sm text-muted-foreground">Convert audio to any format. Pick as many formats as you need.</p>
      </header>

      <section
        className={`flex flex-col items-center justify-center gap-3 rounded-2xl px-6 py-10 text-center ${dragging ? "bg-[var(--bg-field)]" : "bg-card"}`}
      >
        <UploadSimpleIcon size={32} className="text-muted-foreground" />
        <div className="flex flex-col gap-1">
          <p className="font-medium">{dragging ? "Drop to add" : "Drop audio here"}</p>
          <p className="text-sm text-muted-foreground">WAV, FLAC, MP3, AAC, Ogg, Opus, and anything else ffmpeg reads.</p>
        </div>
        <Button variant="outline" disabled={pending} onClick={() => void chooseFiles()}>
          <FolderOpenIcon size={16} />
          Choose audio
        </Button>
      </section>

      {files.length ? (
        <ul className="flex flex-col gap-2">
          {files.map((item) => (
            <li key={item.path} className="flex items-center gap-3 rounded-xl bg-card px-4 py-3">
              {item.ok ? (
                <FileAudioIcon size={20} className="shrink-0 text-muted-foreground" />
              ) : (
                <WarningCircleIcon size={20} className="shrink-0 text-destructive" />
              )}
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-sm font-medium">{item.name}</span>
                <span className={`truncate text-xs ${item.ok ? "text-muted-foreground" : "text-destructive"}`}>
                  {item.ok ? details(item) : item.error}
                </span>
              </div>
              <button
                type="button"
                aria-label={`Remove ${item.name}`}
                disabled={pending}
                className="flex size-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-[var(--button-neutral-hover)] hover:text-foreground disabled:opacity-50"
                onClick={() => setFiles((current) => current.filter((entry) => entry.path !== item.path))}
              >
                <XIcon size={16} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <section className="flex flex-col gap-5">
        <FormatGroup label="Lossless" items={lossless} chosen={chosen} disabled={pending} onToggle={toggle} />
        <FormatGroup label="Lossy" items={lossy} chosen={chosen} disabled={pending} onToggle={toggle} />
      </section>

      <div className="flex gap-2">
        <div className="flex h-10 min-w-0 flex-1 items-center rounded-lg bg-card px-4 text-sm">
          <span className="truncate text-muted-foreground">{output || "Saves next to each file"}</span>
        </div>
        {output ? (
          <Button variant="outline" disabled={pending} onClick={() => setOutput("")}>
            Reset
          </Button>
        ) : null}
        <Button variant="outline" disabled={pending} onClick={() => void chooseFolder()}>
          <FolderOpenIcon size={16} />
          Folder
        </Button>
      </div>

      <div className="flex gap-2">
        <Button className="h-12 flex-1 text-base" disabled={pending || !count} onClick={() => void convert()}>
          {pending ? "Converting…" : count ? `Convert ${count} ${count === 1 ? "file" : "files"}` : "Convert"}
        </Button>
        {pending ? (
          <Button variant="outline" className="h-12 px-6 text-base" onClick={stop}>
            Stop
          </Button>
        ) : null}
      </div>

      {state ? (
        <div className="flex flex-col gap-2">
          <Progress value={Math.round(state.progress * 100)} />
          <p className="text-sm text-muted-foreground">
            {state.done
              ? `${state.outputs.length} of ${state.total} saved in ${state.elapsed.toFixed(1)} s`
              : `${state.current || "Starting"} · ${Math.min(state.finished + 1, state.total)} of ${state.total}`}
          </p>
        </div>
      ) : null}
      {message ? <p className="text-sm">{message}</p> : null}

      {state && (state.outputs.length || state.failures.length) ? (
        <ul className="flex flex-col gap-2">
          {state.outputs.map((item) => (
            <li key={item.path} className="flex items-center gap-3 rounded-xl bg-card px-4 py-3">
              <CheckCircleIcon size={20} weight="fill" className="shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate text-sm">{item.name}</span>
              <Badge>{item.format}</Badge>
              <Button variant="link" className="h-8 px-0" onClick={() => void host()?.reveal?.(item.path)}>
                Show in folder
              </Button>
            </li>
          ))}
          {state.failures.map((item, index) => (
            <li key={`${item.path}-${index}`} className="flex items-center gap-3 rounded-xl bg-card px-4 py-3">
              <WarningCircleIcon size={20} className="shrink-0 text-destructive" />
              <span className="min-w-0 flex-1 truncate text-sm">
                {basename(item.path)}
                {item.format ? ` → ${item.format}` : ""}
              </span>
              <span className="max-w-[50%] truncate text-xs text-destructive">{item.error}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  )
}

const codecs: Record<string, string> = {
  pcm_s16le: "PCM 16-bit",
  pcm_s16be: "PCM 16-bit",
  pcm_s24le: "PCM 24-bit",
  pcm_s24be: "PCM 24-bit",
  pcm_s32le: "PCM 32-bit",
  pcm_s32be: "PCM 32-bit",
  pcm_f32le: "PCM 32-bit float",
  pcm_f32be: "PCM 32-bit float",
  pcm_f64le: "PCM 64-bit float",
  pcm_u8: "PCM 8-bit",
  flac: "FLAC",
  alac: "ALAC",
  wavpack: "WavPack",
  mp3: "MP3",
  mp3float: "MP3",
  aac: "AAC",
  vorbis: "Vorbis",
  opus: "Opus",
  wmav2: "WMA",
  ac3: "AC3",
  eac3: "E-AC3",
}

function codec(name?: string) {
  if (!name) return ""
  const key = name.split(" ")[0].toLowerCase()
  return codecs[key] ?? key.toUpperCase()
}

function details(item: Source) {
  const parts = [codec(item.codec)]
  if (item.rate) parts.push(rate(item.rate))
  if (item.channels) parts.push(channels(item.channels))
  if (item.duration) parts.push(duration(item.duration))
  if (item.bitrate) parts.push(`${item.bitrate} kb/s`)
  return parts.filter(Boolean).join(" · ")
}

function FormatGroup({
  label,
  items,
  chosen,
  disabled,
  onToggle,
}: {
  label: string
  items: Format[]
  chosen: string[]
  disabled: boolean
  onToggle: (id: string) => void
}) {
  if (!items.length) return null
  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => {
          const on = chosen.includes(item.id)
          return (
            <Button
              key={item.id}
              variant={on ? "default" : "outline"}
              aria-pressed={on}
              disabled={disabled}
              className="h-9 px-4"
              onClick={() => onToggle(item.id)}
            >
              {item.label}
              <span className={on ? "opacity-60" : "text-muted-foreground"}>.{item.ext}</span>
            </Button>
          )
        })}
      </div>
    </div>
  )
}
