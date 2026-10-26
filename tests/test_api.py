"""Authentication and record ownership at the HTTP boundary."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from api import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / "tmp"
        temporary_root.mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=temporary_root)
        self.app = create_app(Path(self.temp.name) / "api.db")
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login(self, username, password):
        response = self.client.post("/api/login", json=dict(username=username, password=password))
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.json["token"]}

    def test_full_http_account_and_marks_flow(self):
        self.assertTrue(self.client.get("/api/status").json["setup_needed"])
        self.assertEqual(self.client.get("/api/records").status_code, 403)
        response = self.client.post("/api/setup", json=dict(username="FAC01", name="Teacher", email="teacher@example.org", password="teacher-pass"))
        self.assertEqual(response.status_code, 200)
        faculty = self.login("FAC01", "teacher-pass")
        for username in ("REG01", "REG02"):
            response = self.client.post("/api/accounts", headers=faculty, json=dict(username=username, name="Student", email=username + "@example.org", initial_password="initial-pass"))
            self.assertEqual(response.status_code, 200)
        self.client.post("/api/courses", headers=faculty, json=dict(code="PY01", name="Python"))
        self.client.post("/api/enrolments", headers=faculty, json=dict(student_id="REG01", course_code="PY01"))
        response = self.client.post("/api/marks", headers=faculty, json=dict(student_id="REG01", course_code="PY01", assessment="Exam", assessment_date="2020-01-01", score=80, max_score=100))
        self.assertEqual(response.status_code, 200)
        student = self.login("REG01", "initial-pass")
        self.assertEqual(self.client.get("/api/records", headers=student).status_code, 403)
        self.client.post("/api/password", headers=student, json=dict(old_password="initial-pass", new_password="student-pass"))
        records = self.client.get("/api/records", headers=student)
        self.assertEqual(records.json["marks"][0]["score"], 80)
        self.assertNotIn("users", records.json)
        self.assertEqual(self.client.get("/api/records?student_id=REG02", headers=student).status_code, 403)
        self.assertEqual(self.client.post("/api/courses", headers=student, json=dict(code="OTHER", name="Other")).status_code, 403)
        self.assertEqual(self.client.get("/api/audit", headers=student).status_code, 403)
        self.assertEqual(self.client.post("/api/__dict__", headers=faculty, json={}).status_code, 404)
        self.assertEqual(self.client.post("/api/marks", headers=faculty, json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/courses", headers=faculty, json=[]).status_code, 400)
        self.client.post("/api/logout", headers=student, json={})
        self.assertEqual(self.client.get("/api/me", headers=student).status_code, 403)


if __name__ == "__main__":
    unittest.main()
