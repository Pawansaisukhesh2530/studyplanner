"""Real workflows use temporary records; no test data enters the application DB."""

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET

from growth_planner.database import open_database
from growth_planner.reports import analyse_marks, assessment_ranking, schedule, xml_report
from growth_planner.service import AccessError, Planner
from growth_planner.validation import time_range


class PlannerTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "tmp"
        temporary_root.mkdir(exist_ok=True)
        self.directory = TemporaryDirectory(dir=temporary_root)
        self.path = Path(self.directory.name) / "test.db"
        self.planner = Planner(self.path)
        self.assertTrue(self.planner.setup_needed())
        self.planner.setup_faculty("FAC01", "Test Teacher", "teacher@example.org", "teacher-pass")
        self.faculty = self.planner.login("FAC01", "teacher-pass")
        for student in ("REG01", "REG02"):
            self.planner.save_user(self.faculty, student, "Test Student", student + "@example.org", initial_password="initial-pass")
        self.student = self.planner.login("REG01", "initial-pass")
        self.planner.change_password(self.student, "initial-pass", "student-pass")
        self.planner.save_course(self.faculty, "PY01", "Python", 40)
        self.planner.enrol_student(self.faculty, "REG01", "PY01")
        self.today = date.today().isoformat()

    def tearDown(self):
        self.directory.cleanup()

    def test_setup_permissions_and_passwords(self):
        with self.assertRaises(AccessError):
            self.planner.setup_faculty("FAC02", "Second", "second@example.org", "password2")
        with self.assertRaises(AccessError):
            self.planner.save_course(self.student, "BAD", "Other", 40)
        with self.assertRaises(AccessError):
            self.planner.snapshot(self.student, "REG02")
        initial = self.planner.login("REG02", "initial-pass")
        with self.assertRaises(AccessError):
            self.planner.snapshot(initial)
        self.assertTrue(self.planner.current_user(initial)["must_change_password"])
        self.assertNotIn("password_hash", self.planner.current_user(self.student))
        self.planner.logout(self.student)
        with self.assertRaises(AccessError):
            self.planner.snapshot(self.student)

    def test_marks_import_is_atomic_and_corrections_persist(self):
        self.planner.save_mark(self.faculty, "REG01", "PY01", "Unit 1", self.today, 40, 50)
        self.planner.save_mark(self.faculty, "REG01", "PY01", "Unit 1", self.today, 45, 50)
        records = Planner(self.path).snapshot(self.student)["marks"]
        self.assertEqual(len(records), 1)
        self.assertEqual(analyse_marks(records)["overall"], 90)
        header = "student_id,course_code,assessment,assessment_date,score,max_score\n"
        invalid = header + f"REG01,PY01,Unit 2,{self.today},30,50\nREG02,PY01,Unit 2,{self.today},20,50\n"
        with self.assertRaisesRegex(ValueError, "row 3"):
            self.planner.import_marks(self.faculty, invalid)
        self.assertEqual(len(self.planner.snapshot(self.student)["marks"]), 1)
        for invalid_score in (float("nan"), float("inf"), -1, 51):
            with self.assertRaises(ValueError):
                self.planner.save_mark(self.faculty, "REG01", "PY01", "Invalid", self.today, invalid_score, 50)

    def test_assignments_tasks_and_ownership(self):
        self.planner.save_assignment(self.faculty, "PY01", "Loops", "Write a loop", self.today)
        assignment = self.planner.snapshot(self.student)["assignments"][0]
        self.planner.set_assignment_completion(self.student, assignment["id"], True)
        self.assertIsNotNone(self.planner.snapshot(self.faculty)["completions"][0]["completed_at"])
        self.planner.save_task(self.student, "Revise", "Python", self.today)
        task = self.planner.snapshot(self.student)["tasks"][0]
        self.planner.save_task(self.student, "Revise", "Python", self.today, task["id"], "Done")
        self.assertEqual(self.planner.snapshot(self.student)["tasks"][0]["status"], "Done")
        with self.assertRaises(AccessError):
            self.planner.save_task(self.student, "No", "Python", self.today, 999, "Done")

    def test_clubs_activities_schedule_and_reports(self):
        self.planner.save_club(self.faculty, "CODE", "Programming", "Club", "Weekly practice", "coding", "projects", "python", 2, "Workshops", "May practise teamwork")
        self.planner.save_preferences(self.student, "Coding, Technology", "projects", 3)
        self.planner.set_membership(self.student, "CODE", "Interested")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.planner.save_event(self.faculty, "CODE", "Workshop", yesterday + "T10:00", yesterday + "T12:00", "Lab")
        self.planner.save_study_session(self.student, "Revision", yesterday + "T11:00", yesterday + "T12:30")
        self.planner.save_study_session(self.student, "After", yesterday + "T12:30", yesterday + "T13:00")
        self.planner.save_activity(self.student, "CODE", yesterday, "Wrote a program", 1.5, "Python", event_id=1)
        snapshot = self.planner.snapshot(self.student)
        self.assertEqual(len(schedule(snapshot)["clashes"]), 1)
        self.assertEqual(snapshot["activities"][0]["hours"], 1.5)
        self.assertEqual(snapshot["profile"]["interests"], "coding|technology")
        report = ET.fromstring(xml_report(snapshot))
        self.assertEqual(report.find("profile/record/username").text, "REG01")
        self.assertNotIn(b"password", xml_report(snapshot))

    def test_empty_database_and_comparable_rankings(self):
        empty = Planner(Path(self.directory.name) / "empty.db")
        self.assertTrue(empty.setup_needed())
        with open_database(empty.database_file) as db:
            for table in ("users", "marks", "clubs", "events", "tasks"):
                self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0)
        ranked = assessment_ranking([
            dict(course_code="PY", assessment="A", assessment_date=self.today, max_score=50, score=40),
            dict(course_code="PY", assessment="A", assessment_date=self.today, max_score=50, score=45),
            dict(course_code="PY", assessment="B", assessment_date=self.today, max_score=50, score=10)])
        self.assertEqual([row["rank"] for row in ranked], [2, 1, 1])
        self.assertEqual([row["group_size"] for row in ranked], [2, 2, 1])

    def test_other_students_cannot_update_owned_records(self):
        second = self.planner.login("REG02", "initial-pass")
        self.planner.change_password(second, "initial-pass", "second-pass")
        self.planner.save_task(self.student, "My work", "Python", self.today)
        self.planner.save_study_session(self.student, "My session", self.today + "T10:00", self.today + "T11:00")
        self.planner.save_club(self.faculty, "CODE", "Coding", "Club", "Practice", "coding", "projects", "python", 2, "Workshop", "May build skills")
        self.planner.save_activity(self.student, "CODE", self.today, "Practice", 1, "python")
        actions = [
            lambda: self.planner.save_task(second, "Changed", "Python", self.today, 1),
            lambda: self.planner.save_study_session(second, "Changed", self.today + "T10:00", self.today + "T11:00", 1),
            lambda: self.planner.save_activity(second, "CODE", self.today, "Changed", 1, "python", activity_id=1),
            lambda: self.planner.class_marks(second),
            lambda: self.planner.audit_text(second),
            lambda: self.planner.save_college_holiday(second, self.today, "Changed"),
        ]
        for action in actions:
            with self.assertRaises(AccessError):
                action()
        self.assertEqual(self.planner.snapshot(self.student)["tasks"][0]["title"], "My work")
        with self.assertRaises(ValueError):
            time_range(self.today + "T10:00:01", self.today + "T10:00:30")


if __name__ == "__main__":
    unittest.main()
