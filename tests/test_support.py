"""Backup round trips and holiday success/failure parsing."""

from pathlib import Path
from contextlib import closing
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from growth_planner.backup import create_backup, restore_backup, validate_backup
from growth_planner.holidays import fetch_holidays
from growth_planner.service import AccessError, Planner


class SupportTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "tmp"
        temporary_root.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=temporary_root)
        self.path = Path(self.temp.name)
        self.planner = Planner(self.path / "app.db")
        self.planner.setup_faculty("FAC01", "Teacher", "teacher@example.org", "teacher-pass")
        self.token = self.planner.login("FAC01", "teacher-pass")

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_restore_and_invalid_file(self):
        self.planner.save_course(self.token, "PY", "Python")
        backup = self.path / "saved.db"
        backup.write_bytes(create_backup(self.planner, self.token))
        validate_backup(backup)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)
        self.planner.save_course(self.token, "DB", "Databases")
        safety = restore_backup(self.planner, self.token, backup)
        validate_backup(safety)
        with self.assertRaises(AccessError):
            self.planner.current_user(self.token)
        token = self.planner.login("FAC01", "teacher-pass")
        self.assertEqual([row["code"] for row in self.planner.snapshot(token)["courses"]], ["PY"])
        invalid = self.path / "not_a_backup.db"
        invalid.write_text("invalid", encoding="utf-8")
        with self.assertRaises(ValueError):
            restore_backup(self.planner, token, invalid)
        self.assertEqual(len(self.planner.snapshot(token)["courses"]), 1)
        self.assertIn("restore backup", self.planner.audit_text(token))

    def test_college_calendar_and_enrolment_corrections(self):
        self.planner.save_college_holiday(self.token, "2026-01-01", "College closure")
        self.planner.save_college_holiday(self.token, "2026-01-01", "Corrected closure")
        self.assertEqual(self.planner.snapshot(self.token)["college_holidays"][0]["name"], "Corrected closure")
        self.planner.remove_college_holiday(self.token, "2026-01-01")
        self.assertEqual(self.planner.snapshot(self.token)["college_holidays"], [])
        self.planner.save_user(self.token, "REG01", "Student", "student@example.org", initial_password="initial-pass")
        self.planner.save_course(self.token, "PY", "Python")
        self.planner.enrol_student(self.token, "REG01", "PY")
        self.planner.save_assignment(self.token, "PY", "Work", "Instructions", "2026-01-01")
        self.assertEqual(len(self.planner.snapshot(self.token, "REG01")["assignments"]), 1)
        self.planner.enrol_student(self.token, "REG01", "PY", False)
        self.assertEqual(self.planner.snapshot(self.token, "REG01")["assignments"], [])

    @patch("growth_planner.holidays.get_json")
    def test_holidays_are_validated_and_region_filtered(self, get_json):
        get_json.side_effect = [[{"countryCode": "US"}], [
            {"date": "2026-01-01", "name": "New Year", "global": True, "counties": None, "types": ["Public"]},
            {"date": "2026-03-01", "name": "Regional", "global": False, "counties": ["US-TX"], "types": ["Public"]}]]
        result = fetch_holidays("us", 2026, "US-CA")
        self.assertEqual(len(result), 1)
        get_json.side_effect = None
        get_json.return_value = [{"countryCode": "US"}]
        with self.assertRaisesRegex(ValueError, "does not currently support IN"):
            fetch_holidays("IN", 2026)
        get_json.side_effect = ValueError("offline")
        with self.assertRaisesRegex(ValueError, "offline"):
            fetch_holidays("US", 2026)


if __name__ == "__main__":
    unittest.main()
