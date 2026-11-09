import shutil
import tempfile
import unittest
from pathlib import Path

import ox1audio as ox

import app

TONE = Path(__file__).with_name("tone.wav")


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.song = self.folder / "song.wav"
        shutil.copy(TONE, self.song)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_one_file_becomes_one_copy_per_format_next_to_it(self):
        run = ox.test(app.convert, files=[self.song], formats=["flac", "mp3", "wav"])
        names = sorted(Path(item["path"]).name for item in run["items"])
        self.assertEqual(names, ["song.flac", "song.mp3", "song.wav"])
        self.assertTrue(all(Path(item["path"]).parent == self.folder for item in run["items"]))
        titles = {Path(item["path"]).suffix: item["title"] for item in run["items"]}
        self.assertEqual(titles, {".flac": "song", ".mp3": "song", ".wav": "song (already WAV)"}, "the song itself is named as such (GAB-152)")
        for item in run["items"]:
            self.assertAlmostEqual(item["metadata"]["duration"], ox.audio.probe(item["path"]).duration, delta=0.05)
        self.assertEqual(run["progress"][-1][1], "song.wav to MP3")  # formats run in the order they are offered

    def test_the_format_a_song_already_is_makes_no_second_copy(self):
        run = ox.test(app.convert, files=[self.song], formats=["wav"])
        self.assertEqual([item["path"] for item in run["items"]], [str(self.song)])  # the song itself goes to the Library
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["song.wav"])

    def test_a_16_bit_song_stays_16_bit(self):
        out = self.folder / "out"
        out.mkdir()
        run = ox.test(app.convert, files=[self.song], formats=["wav", "aiff", "flac"], folder=out)
        self.assertEqual([ox.audio.probe(item["path"]).bits for item in run["items"]], [16, 16, 16])

    def test_stop_keeps_the_copies_that_were_finished(self):
        with self.assertRaises(ox.Cancelled) as stopped:
            ox.test(app.convert, files=[self.song], formats=["flac", "mp3", "opus"], stop_at=0.67)
        self.assertEqual([Path(item["path"]).name for item in stopped.exception.kept], ["song.flac", "song.mp3"])
        self.assertFalse((self.folder / "song.opus").exists())

    def test_a_chosen_folder_gets_the_copies(self):
        out = self.folder / "out"
        out.mkdir()
        run = ox.test(app.convert, files=[self.song], formats=["opus"], folder=out)
        self.assertEqual(Path(run["items"][0]["path"]).parent, out)

    def test_a_song_from_open_with_is_never_written_next_to(self):
        # Open with hands over one read-only file (GAB-46): the copies go to the Library, not its folder.
        run = ox.test(app.convert, open_with=[self.song], formats=["flac", "mp3"])
        self.assertEqual(sorted(Path(item["path"]).name for item in run["items"]), ["song.flac", "song.mp3"])
        self.assertTrue(all(Path(item["path"]).parent != self.folder for item in run["items"]))
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), ["song.wav"])

    def test_open_with_in_the_format_it_already_is_makes_no_copy(self):
        run = ox.test(app.convert, open_with=[self.song], formats=["wav", "mp3"])
        self.assertEqual([Path(item["path"]).suffix for item in run["items"]], [".mp3"])
        with self.assertRaises(ox.Problem) as caught:
            ox.test(app.convert, open_with=[self.song], formats=["wav"])
        self.assertEqual(str(caught.exception), "Your Library already has this in that format.")

    def test_a_chosen_folder_still_wins_after_open_with(self):
        out = self.folder / "out"
        out.mkdir()
        run = ox.test(app.convert, open_with=[self.song], formats=["mp3"], folder=out)
        self.assertEqual(Path(run["items"][0]["path"]).parent, out)

    def test_every_format_is_one_this_computer_can_write(self):
        for kind in app.FORMATS:
            with self.subTest(kind=kind):
                run = ox.test(app.convert, files=[self.song], formats=[kind])
                self.assertEqual(ox.audio.probe(run["items"][0]["path"]).rate in (44100, 48000), True)

    def test_a_file_that_is_not_audio_says_so_plainly(self):
        notes = self.folder / "notes.wav"
        notes.write_text("not audio")
        with self.assertRaises(ox.Problem) as caught:
            ox.test(app.convert, files=[notes], formats=["mp3"])
        self.assertEqual(str(caught.exception), "notes.wav isn't a sound file Mixel can open.")


if __name__ == "__main__":
    unittest.main()
