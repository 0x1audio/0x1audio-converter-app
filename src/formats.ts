export interface Format {
  id: string
  label: string
  ext: string
  lossless: boolean
}

// Shown until the worker answers with the formats this computer can write.
export const fallback: Format[] = [
  { id: "wav", label: "WAV", ext: "wav", lossless: true },
  { id: "aiff", label: "AIFF", ext: "aiff", lossless: true },
  { id: "flac", label: "FLAC", ext: "flac", lossless: true },
  { id: "alac", label: "ALAC", ext: "m4a", lossless: true },
  { id: "wavpack", label: "WavPack", ext: "wv", lossless: true },
  { id: "mp3", label: "MP3", ext: "mp3", lossless: false },
  { id: "aac", label: "AAC", ext: "m4a", lossless: false },
  { id: "ogg", label: "Ogg Vorbis", ext: "ogg", lossless: false },
  { id: "opus", label: "Opus", ext: "opus", lossless: false },
  { id: "wma", label: "WMA", ext: "wma", lossless: false },
  { id: "ac3", label: "AC3", ext: "ac3", lossless: false },
]
