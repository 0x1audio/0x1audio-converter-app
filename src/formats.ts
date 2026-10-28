export interface Format {
  id: string
  label: string
  ext: string
  lossless: boolean
  depths: string[]
  bitrates: number[]
}

// Shown until the worker answers with the formats this computer can write.
export const fallback: Format[] = [
  { id: "wav", label: "WAV", ext: "wav", lossless: true, depths: ["16", "24", "32", "32f"], bitrates: [] },
  { id: "aiff", label: "AIFF", ext: "aiff", lossless: true, depths: ["16", "24", "32"], bitrates: [] },
  { id: "flac", label: "FLAC", ext: "flac", lossless: true, depths: ["16", "24"], bitrates: [] },
  { id: "alac", label: "ALAC", ext: "m4a", lossless: true, depths: ["16", "24"], bitrates: [] },
  { id: "wavpack", label: "WavPack", ext: "wv", lossless: true, depths: ["16", "24", "32f"], bitrates: [] },
  { id: "mp3", label: "MP3", ext: "mp3", lossless: false, depths: [], bitrates: [128, 160, 192, 256, 320] },
  { id: "aac", label: "AAC", ext: "m4a", lossless: false, depths: [], bitrates: [96, 128, 160, 192, 256, 320] },
  { id: "ogg", label: "Ogg Vorbis", ext: "ogg", lossless: false, depths: [], bitrates: [96, 128, 160, 192, 256, 320] },
  { id: "opus", label: "Opus", ext: "opus", lossless: false, depths: [], bitrates: [64, 96, 128, 160, 192, 256] },
  { id: "wma", label: "WMA", ext: "wma", lossless: false, depths: [], bitrates: [128, 160, 192, 256, 320] },
  { id: "ac3", label: "AC3", ext: "ac3", lossless: false, depths: [], bitrates: [192, 256, 384, 448, 640] },
]

export const rates = [
  { value: "keep", label: "Keep original" },
  { value: "22050", label: "22.05 kHz" },
  { value: "44100", label: "44.1 kHz" },
  { value: "48000", label: "48 kHz" },
  { value: "88200", label: "88.2 kHz" },
  { value: "96000", label: "96 kHz" },
  { value: "192000", label: "192 kHz" },
]

export const channelOptions = [
  { value: "keep", label: "Keep original" },
  { value: "1", label: "Mono" },
  { value: "2", label: "Stereo" },
]

export const depths = [
  { value: "16", label: "16-bit" },
  { value: "24", label: "24-bit" },
  { value: "32", label: "32-bit" },
  { value: "32f", label: "32-bit float" },
]

export const bitrates = [96, 128, 160, 192, 256, 320].map((value) => ({ value: String(value), label: `${value} kb/s` }))
