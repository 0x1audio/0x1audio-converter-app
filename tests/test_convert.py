import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio import channel_count, probe  # noqa: E402
from convert import Settings, available, convert, find, plan  # noqa: E402


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        rate = 44100
        t = np.arange(rate * 2) / rate
        tone = 0.3 * np.sin(2 * np.pi * 440 * t)
        self.source = self.dir / "tone.wav"
        sf.write(self.source, np.stack([tone, tone], axis=1), rate, subtype="PCM_16")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_probe_reads_a_wav(self):
        info = probe(str(self.source))
        self.assertEqual(info.rate, 44100)
        self.assertEqual(info.channels, 2)
        self.assertAlmostEqual(info.duration, 2.0, places=1)

    def test_every_format_round_trips(self):
        out = self.dir / "out"
        for fmt in available():
            with self.subTest(fmt=fmt.id):
                written = convert(str(self.source), fmt.id, str(out), Settings(depth="24", bitrate=192))
                self.assertEqual(written.suffix, f".{fmt.ext}")
                info = probe(str(written))
                self.assertAlmostEqual(info.duration, 2.0, delta=0.2)
                expected = 48000 if fmt.id == "opus" else 44100
                self.assertEqual(info.rate, expected)

    def test_names_never_overwrite_the_source_or_each_other(self):
        source = probe(str(self.source))
        wav = find("wav")
        taken: set[Path] = set()
        first = plan(source, wav, self.dir, Settings(), taken)
        second = plan(source, wav, self.dir, Settings(), taken)
        self.assertNotEqual(first.target, self.source)
        self.assertNotEqual(first.target, second.target)

    def test_mp3_caps_rate_and_channels(self):
        source = probe(str(self.source))
        step = plan(source, find("mp3"), self.dir, Settings(rate=96000, channels=6))
        args = step.args
        self.assertEqual(args[args.index("-ar") + 1], "48000")
        self.assertEqual(args[args.index("-ac") + 1], "2")

    def test_channel_layouts(self):
        self.assertEqual(channel_count("mono"), 1)
        self.assertEqual(channel_count("5.1(side)"), 6)
        self.assertEqual(channel_count("3 channels"), 3)


if __name__ == "__main__":
    unittest.main()
