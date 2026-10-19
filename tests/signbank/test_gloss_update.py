import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recordings.services.signbank_service import SignbankService


class TestGlossUpdate(unittest.TestCase):

    def test_gloss_update_moves_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "signbank.db"
            video_root = root / "glossvideo"

            # Maak een minimale testdatabase.
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE dictionary_gloss (
                        id INTEGER PRIMARY KEY,
                        annotation_idgloss TEXT UNIQUE,
                        subhndsh INTEGER,
                        final_subhndsh INTEGER,
                        locprim INTEGER,
                        final_loc INTEGER,
                        semField TEXT,
                        semField1 TEXT,
                        semField2 TEXT,
                        semField3 TEXT,
                        semField4 TEXT,
                        inWeb INTEGER,
                        lastUpdated TEXT
                    )
                """)
                conn.execute(
                    """
                    INSERT INTO dictionary_gloss
                    (id, annotation_idgloss)
                    VALUES (?, ?)
                    """,
                    (1063, "BEELD-B"),
                )

            # Maak een testvideo.
            old_video = video_root / "BE" / "BEELD-B-1063.mp4"
            old_video.parent.mkdir(parents=True)
            old_video.write_bytes(b"testvideo")

            # Gebruik uitsluitend de tijdelijke testbestanden.
            service = SignbankService()
            service.db_path = str(db_path)
            service.video_root = str(video_root)

            service.update_gloss(
                1063,
                "BEELD-B",
                "AFBEELDING-B",
            )

            # Controleer de database.
            with sqlite3.connect(db_path) as conn:
                gloss = conn.execute(
                    """
                    SELECT annotation_idgloss
                    FROM dictionary_gloss
                    WHERE id = 1063
                    """
                ).fetchone()[0]

            self.assertEqual(gloss, "AFBEELDING-B")

            # Controleer de video.
            new_video = video_root / "AF" / "AFBEELDING-B-1063.mp4"

            self.assertFalse(old_video.exists())
            self.assertTrue(new_video.exists())
            self.assertEqual(new_video.read_bytes(), b"testvideo")

    def test_duplicate_gloss_does_not_move_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "signbank.db"
            video_root = root / "glossvideo"

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE dictionary_gloss (
                        id INTEGER PRIMARY KEY,
                        annotation_idgloss TEXT UNIQUE,
                        subhndsh INTEGER,
                        final_subhndsh INTEGER,
                        locprim INTEGER,
                        final_loc INTEGER,
                        semField TEXT,
                        semField1 TEXT,
                        semField2 TEXT,
                        semField3 TEXT,
                        semField4 TEXT,
                        inWeb INTEGER,
                        lastUpdated TEXT
                    )
                """)
                conn.executemany(
                    """
                    INSERT INTO dictionary_gloss
                    (id, annotation_idgloss)
                    VALUES (?, ?)
                    """,
                    [
                        (1063, "BEELD-B"),
                        (2000, "AFBEELDING-B"),
                    ],
                )

            old_video = video_root / "BE" / "BEELD-B-1063.mp4"
            old_video.parent.mkdir(parents=True)
            old_video.write_bytes(b"testvideo")

            service = SignbankService()
            service.db_path = str(db_path)
            service.video_root = str(video_root)

            with self.assertRaises(ValueError):
                service.update_gloss(
                    1063,
                    "BEELD-B",
                    "AFBEELDING-B",
                )

            with sqlite3.connect(db_path) as conn:
                gloss = conn.execute(
                    """
                    SELECT annotation_idgloss
                    FROM dictionary_gloss
                    WHERE id = 1063
                    """
                ).fetchone()[0]

            self.assertEqual(gloss, "BEELD-B")
            self.assertTrue(old_video.exists())
            self.assertFalse(
                (video_root / "AF" / "AFBEELDING-B-1063.mp4").exists()
            )
    def test_database_failure_restores_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "signbank.db"
            video_root = root / "glossvideo"

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE dictionary_gloss (
                        id INTEGER PRIMARY KEY,
                        annotation_idgloss TEXT UNIQUE,
                        subhndsh INTEGER,
                        final_subhndsh INTEGER,
                        locprim INTEGER,
                        final_loc INTEGER,
                        semField TEXT,
                        semField1 TEXT,
                        semField2 TEXT,
                        semField3 TEXT,
                        semField4 TEXT,
                        inWeb INTEGER,
                        lastUpdated TEXT
                    )
                """)
                conn.execute("""
                    INSERT INTO dictionary_gloss
                    (id, annotation_idgloss)
                    VALUES (1063, 'BEELD-B')
                """)

                conn.execute("""
                    CREATE TRIGGER reject_gloss_update
                    BEFORE UPDATE OF annotation_idgloss
                    ON dictionary_gloss
                    BEGIN
                        SELECT RAISE(ABORT, 'Simulated database failure');
                    END
                """)

            old_video = video_root / "BE" / "BEELD-B-1063.mp4"
            new_video = video_root / "AF" / "AFBEELDING-B-1063.mp4"

            old_video.parent.mkdir(parents=True)
            old_video.write_bytes(b"testvideo")

            service = SignbankService()
            service.db_path = str(db_path)
            service.video_root = str(video_root)

            with self.assertRaises(sqlite3.IntegrityError):
                service.update_gloss(
                    1063,
                    "BEELD-B",
                    "AFBEELDING-B",
                )

            with sqlite3.connect(db_path) as conn:
                gloss = conn.execute("""
                    SELECT annotation_idgloss
                    FROM dictionary_gloss
                    WHERE id = 1063
                """).fetchone()[0]

            self.assertEqual(gloss, "BEELD-B")
            self.assertTrue(old_video.exists())
            self.assertEqual(old_video.read_bytes(), b"testvideo")
            self.assertFalse(new_video.exists())

if __name__ == "__main__":
    unittest.main()