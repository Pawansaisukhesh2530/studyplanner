"""Real Qt buttons -> HTTP -> Flask -> SQLite, using temporary test records."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication, QMessageBox
from werkzeug.serving import make_server

from api import create_app
from faculty_desktop import ApiClient, FacultyWindow, configure_font
from growth_planner.service import Planner


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])
        configure_font(cls.qt)

    def test_desktop_login_and_save_buttons_through_live_api(self):
        root = Path(__file__).resolve().parents[1]
        (root / "tmp").mkdir(exist_ok=True)
        with TemporaryDirectory(dir=root / "tmp") as folder:
            path = Path(folder) / "desktop.db"
            planner = Planner(path)
            planner.setup_faculty("FAC01", "Teacher", "teacher@example.org", "teacher-pass")
            server = make_server("127.0.0.1", 0, create_app(path))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            window = FacultyWindow(ApiClient("http://127.0.0.1:" + str(server.server_port)))
            try:
                with patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning") as warning:
                    window.username.setText("FAC01")
                    window.password.setText("teacher-pass")
                    window.login_button.click()
                    self.assertTrue(window.tabs.isTabEnabled(1))
                    account = window.forms["Accounts"]
                    for field, value in dict(username="REG01", name="Student", email="student@example.org", initial_password="initial-pass").items():
                        account.inputs[field].setText(value)
                    account.save_button.click()
                    course = window.forms["Subjects"]
                    course.inputs["code"].setText("PY01")
                    course.inputs["name"].setText("Python")
                    course.inputs["pass_percentage"].setText("40")
                    course.save_button.click()
                    enrol = window.forms["Enrolments"]
                    enrol.inputs["student_id"].setText("REG01")
                    enrol.inputs["course_code"].setText("PY01")
                    enrol.save_button.click()
                    mark = window.forms["Marks"]
                    for field, value in dict(student_id="REG01", course_code="PY01", assessment="Exam", assessment_date="2020-01-01", score="45", max_score="50").items():
                        mark.inputs[field].setText(value)
                    mark.save_button.click()
                    assignment = window.forms["Assignments"]
                    for field, value in dict(course_code="PY01", title="Loops", due_date="2026-01-01").items():
                        assignment.inputs[field].setText(value)
                    assignment.inputs["instructions"].setPlainText("Practise loops")
                    assignment.save_button.click()
                    club = window.forms["Clubs"]
                    for field, value in dict(club_id="CODE", name="Coding", category="Club", interests="coding", goals="projects", skills="python", hours_per_week="2").items():
                        club.inputs[field].setText(value)
                    for field, value in dict(description="Weekly practice", example_activities="Workshops", potential_benefit="May practise teamwork").items():
                        club.inputs[field].setPlainText(value)
                    club.save_button.click()
                    event = window.forms["Events"]
                    for field, value in dict(club_id="CODE", title="Workshop", starts_at="2020-01-01T10:00", ends_at="2020-01-01T11:00", location="Lab").items():
                        event.inputs[field].setText(value)
                    event.save_button.click()
                    faculty = planner.login("FAC01", "teacher-pass")
                    self.assertEqual(planner.snapshot(faculty, "REG01")["marks"][0]["score"], 45)
                    self.assertEqual(len(planner.snapshot(faculty)["all_assignments"]), 1)
                    self.assertEqual(len(planner.snapshot(faculty)["events"]), 1)
                    mark.choose.setCurrentIndex(1)
                    mark.inputs["score"].setText("48")
                    mark.save_button.click()
                    self.assertEqual(planner.snapshot(faculty, "REG01")["marks"][0]["score"], 48)
                    warning.assert_not_called()
                    window.sign_out()
                    self.assertFalse(window.tabs.isTabEnabled(1))
            finally:
                window.close()
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
