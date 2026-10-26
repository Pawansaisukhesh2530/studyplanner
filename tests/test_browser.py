"""Exercise the actual Streamlit screens against an isolated database."""

from datetime import date, timedelta
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from streamlit.testing.v1 import AppTest

from growth_planner.service import Planner


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        (self.root / "tmp").mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=self.root / "tmp")
        self.path = Path(self.temp.name) / "ui.db"
        self.previous = os.environ.get("GROWTH_PLANNER_DB")
        os.environ["GROWTH_PLANNER_DB"] = str(self.path)

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("GROWTH_PLANNER_DB", None)
        else:
            os.environ["GROWTH_PLANNER_DB"] = self.previous
        self.temp.cleanup()

    def app(self, token=None):
        app = AppTest.from_file(str(self.root / "app.py"), default_timeout=20)
        if token:
            app.session_state["token"] = token
        app.run()
        self.assertFalse(app.exception)
        return app

    def test_first_faculty_setup_from_empty_screen(self):
        app = self.app()
        self.assertIn("Create the first faculty account", [item.value for item in app.header])
        for item, value in zip(app.text_input, ["FAC01", "Teacher", "teacher@example.org", "teacher-pass", "teacher-pass"]):
            item.set_value(value)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(Planner(self.path).setup_needed())
        self.assertIn("Sign in", [item.value for item in app.header])

    def test_all_faculty_and_student_pages_render(self):
        planner = Planner(self.path)
        planner.setup_faculty("FAC01", "Teacher", "teacher@example.org", "teacher-pass")
        faculty = planner.login("FAC01", "teacher-pass")
        planner.save_user(faculty, "REG01", "Student", "student@example.org", initial_password="initial-pass")
        student = planner.login("REG01", "initial-pass")
        planner.change_password(student, "initial-pass", "student-pass")
        planner.save_course(faculty, "PY01", "Python")
        planner.enrol_student(faculty, "REG01", "PY01")
        when = (date.today() - timedelta(days=1)).isoformat()
        planner.save_mark(faculty, "REG01", "PY01", "Unit 1", when, 40, 50)
        planner.save_assignment(faculty, "PY01", "Practice", "Write code", when)
        planner.save_club(faculty, "CODE", "Coding", "Club", "Practice", "coding", "projects", "python", 2, "Workshop", "May build skills")
        planner.save_event(faculty, "CODE", "Workshop", when + "T10:00", when + "T11:00", "Lab")
        planner.save_task(student, "Revise", "Python", when)
        planner.save_study_session(student, "Study", when + "T12:00", when + "T13:00")
        planner.save_activity(student, "CODE", when, "Practised loops", 1, "python", event_id=1)
        for token in (faculty, student):
            app = self.app(token)
            pages = list(app.sidebar.radio[0].options)
            for page in pages:
                app.sidebar.radio[0].set_value(page).run()
                self.assertFalse(app.exception, page)

    def test_browser_saves_accounts_subjects_and_student_work(self):
        planner = Planner(self.path)
        planner.setup_faculty("FAC01", "Teacher", "teacher@example.org", "teacher-pass")
        faculty = planner.login("FAC01", "teacher-pass")
        app = self.app(faculty)

        def field(elements, label):
            return next(item for item in elements if item.label == label)

        def click(label):
            field(app.button, label).click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)

        for label, value in [("Account ID", "REG01"), ("Full name", "Student"), ("Email", "student@example.org"),
                             ("Initial/reset password (leave empty to keep an existing password)", "initial-pass")]:
            field(app.text_input, label).set_value(value)
        click("Save account")
        field(app.text_input, "Subject code").set_value("PY01")
        field(app.text_input, "Subject name").set_value("Python")
        click("Save subject")
        click("Enrol student")
        app.sidebar.radio[0].set_value("Marks").run()
        field(app.text_input, "Assessment name").set_value("Unit 1")
        field(app.number_input, "Maximum score").set_value(50.0)
        field(app.number_input, "Score").set_value(45.0)
        click("Save marks")
        app.sidebar.radio[0].set_value("Assignments").run()
        field(app.text_input, "Title").set_value("Loops")
        field(app.text_area, "Instructions").set_value("Practise loops")
        click("Save assignment")
        student = planner.login("REG01", "initial-pass")
        app = self.app(student)
        for label, value in [("Current password", "initial-pass"), ("New password", "student-pass"), ("Confirm new password", "student-pass")]:
            field(app.text_input, label).set_value(value)
        click("Change password")
        app.sidebar.radio[0].set_value("Assignments and tasks").run()
        click("Mark complete")
        field(app.text_input, "Task").set_value("Revise")
        field(app.text_input, "Subject").set_value("Python")
        click("Save study task")
        snapshot = planner.snapshot(student)
        self.assertEqual(snapshot["marks"][0]["score"], 45)
        self.assertIsNotNone(snapshot["assignments"][0]["completed_at"])
        self.assertEqual(snapshot["tasks"][0]["title"], "Revise")


if __name__ == "__main__":
    unittest.main()
