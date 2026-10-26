"""Faculty PyQt forms, following the semester's QWidget/form/button pattern."""

import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QFont, QFontDatabase


def configure_font(app):
    """Load the Windows UI font explicitly, including for offscreen verification."""
    font_file = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeui.ttf"
    if font_file.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 10))


class ApiClient:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip("/")
        self.token = ""

    def request(self, path, payload=None):
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + "/api/" + path, data=data, headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            try:
                message = json.load(error).get("error", "Request rejected.")
            except (ValueError, AttributeError):
                message = "The API rejected the request (HTTP " + str(error.code) + ")."
            raise ValueError(message)
        except (URLError, TimeoutError, OSError):
            raise ValueError("Cannot reach the API. Start Start-API.bat, then try again.")


# (field name, user-facing label, field type). Database rules stay in service.py.
FORMS = {
    "Accounts": ("accounts", "users", "username", [
        ("username", "Account ID", "text"), ("name", "Full name", "text"),
        ("email", "Email", "text"), ("role", "Role", "role"),
        ("initial_password", "Initial/reset password (blank keeps existing)", "password")]),
    "Subjects": ("courses", "courses", "code", [
        ("code", "Subject code", "text"), ("name", "Subject name", "text"),
        ("pass_percentage", "Pass percentage", "number")]),
    "Enrolments": ("enrolments", "enrolments", None, [
        ("student_id", "Student ID", "text"), ("course_code", "Subject code", "text")]),
    "Marks": ("marks", "marks", "id", [
        ("student_id", "Student ID", "text"), ("course_code", "Subject code", "text"),
        ("assessment", "Assessment name", "text"), ("assessment_date", "Assessment date (YYYY-MM-DD)", "text"),
        ("score", "Score", "number"), ("max_score", "Maximum score", "number")]),
    "Assignments": ("assignments", "all_assignments", "id", [
        ("course_code", "Subject code", "text"), ("title", "Title", "text"),
        ("instructions", "Instructions", "long"), ("due_date", "Due date (YYYY-MM-DD)", "text")]),
    "Clubs": ("clubs", "clubs", "club_id", [
        ("club_id", "Club ID", "text"), ("name", "Name", "text"), ("category", "Category", "text"),
        ("description", "Description and responsibilities", "long"), ("interests", "Interests (comma separated)", "text"),
        ("goals", "Goals (comma separated)", "text"), ("skills", "Skills (comma separated)", "text"),
        ("hours_per_week", "Expected weekly hours", "number"), ("example_activities", "Typical activities", "long"),
        ("potential_benefit", "Possible benefits", "long")]),
    "Events": ("events", "events", "id", [
        ("club_id", "Club ID", "text"), ("title", "Title", "text"),
        ("starts_at", "Start (YYYY-MM-DDTHH:MM, local time)", "text"),
        ("ends_at", "End (YYYY-MM-DDTHH:MM, local time)", "text"), ("location", "Location", "text")]),
}


class RecordForm(QWidget):
    def __init__(self, client, name, saved):
        super().__init__()
        self.client = client
        self.name = name
        self.saved = saved
        self.operation, self.section, self.identity, self.fields = FORMS[name]
        self.records = []
        self.inputs = {}
        layout = QVBoxLayout()
        self.choose = QComboBox()
        self.choose.addItem("Add new", None)
        self.choose.currentIndexChanged.connect(self.load_record)
        layout.addWidget(QLabel("Choose an existing record to edit, or Add new."))
        layout.addWidget(self.choose)
        form = QFormLayout()
        for field, label, kind in self.fields:
            if kind == "role":
                widget = QComboBox()
                widget.addItems(["student", "faculty"])
            elif kind == "long":
                widget = QTextEdit()
                widget.setMaximumHeight(65)
            else:
                widget = QLineEdit()
                if kind == "password":
                    widget.setEchoMode(QLineEdit.Password)
            self.inputs[field] = widget
            form.addRow(label, widget)
        layout.addLayout(form)
        self.save_button = QPushButton("Save " + name.lower())
        self.save_button.clicked.connect(self.save_record)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def refresh(self, data):
        self.records = data.get(self.section, [])
        self.choose.blockSignals(True)
        self.choose.clear()
        self.choose.addItem("Add new", None)
        if self.identity:
            for record in self.records:
                label = record.get("name", record.get("title", record.get("assessment", "Record")))
                if "student_id" in record:
                    label = record["student_id"] + " · " + label
                self.choose.addItem(str(label) + " (" + str(record[self.identity]) + ")", record[self.identity])
        self.choose.blockSignals(False)
        self.load_record()

    def load_record(self):
        chosen = self.choose.currentData()
        record = next((row for row in self.records if self.identity and row[self.identity] == chosen), {})
        immutable = {self.identity} if self.identity != "id" else set()
        if self.name == "Marks":
            immutable.update(["student_id", "course_code", "assessment", "assessment_date"])
        if self.name == "Assignments":
            immutable.add("course_code")
        if self.name == "Accounts":
            immutable.add("role")
        for field, label, kind in self.fields:
            widget = self.inputs[field]
            widget.setEnabled(not record or field not in immutable)
            default = 40 if field == "pass_percentage" else ""
            value = str(record.get(field, default))
            if kind == "role":
                widget.setCurrentText(value if record else "student")
            elif kind == "long":
                widget.setPlainText(value)
            else:
                widget.setText(value)

    def save_record(self):
        try:
            payload = {}
            for field, label, kind in self.fields:
                widget = self.inputs[field]
                if kind == "role":
                    value = widget.currentText()
                elif kind == "long":
                    value = widget.toPlainText()
                else:
                    value = widget.text()
                if kind == "number":
                    try:
                        value = float(value)
                    except ValueError:
                        raise ValueError(label + " must be a number.")
                payload[field] = value
            chosen = self.choose.currentData()
            if chosen is not None and self.name in ("Assignments", "Events"):
                payload["assignment_id" if self.name == "Assignments" else "event_id"] = chosen
            response = self.client.request(self.operation, payload)
            QMessageBox.information(self, "Saved", str(response["result"]))
            self.saved()
        except ValueError as error:
            QMessageBox.warning(self, "Check the form", str(error))


class FacultyWindow(QMainWindow):
    def __init__(self, client=None):
        super().__init__()
        self.client = client or ApiClient()
        self.setWindowTitle("Student Growth Planner — Faculty")
        self.resize(950, 800)
        self.tabs = QTabWidget()
        self.login_page = QWidget()
        layout = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("Sign in")
        self.login_button.clicked.connect(self.sign_in)
        layout.addRow(QLabel("Start the Flask API first. Create the first faculty account in the browser."))
        layout.addRow("Faculty ID", self.username)
        layout.addRow("Password", self.password)
        layout.addRow(self.login_button)
        self.login_page.setLayout(layout)
        self.tabs.addTab(self.login_page, "Sign in")
        self.forms = {}
        for name in FORMS:
            form = RecordForm(self.client, name, self.refresh_records)
            self.forms[name] = form
            index = self.tabs.addTab(form, name)
            self.tabs.setTabEnabled(index, False)
        account = QWidget()
        account_layout = QFormLayout()
        self.old_password = QLineEdit()
        self.new_password = QLineEdit()
        self.confirm_password = QLineEdit()
        for field in (self.old_password, self.new_password, self.confirm_password):
            field.setEchoMode(QLineEdit.Password)
        account_layout.addRow("Current password", self.old_password)
        account_layout.addRow("New password", self.new_password)
        account_layout.addRow("Confirm new password", self.confirm_password)
        self.password_button = QPushButton("Change password")
        self.password_button.clicked.connect(self.change_password)
        account_layout.addRow(self.password_button)
        self.refresh_button = QPushButton("Refresh records")
        self.refresh_button.clicked.connect(self.refresh_records)
        account_layout.addRow(self.refresh_button)
        self.logout_button = QPushButton("Sign out")
        self.logout_button.clicked.connect(self.sign_out)
        account_layout.addRow(self.logout_button)
        account.setLayout(account_layout)
        self.account_index = self.tabs.addTab(account, "Account")
        self.tabs.setTabEnabled(self.account_index, False)
        self.setCentralWidget(self.tabs)

    def sign_in(self):
        try:
            self.client.token = self.client.request("login", {"username": self.username.text(), "password": self.password.text()})["token"]
            user = self.client.request("me")
            if user["role"] != "faculty":
                self.client.request("logout", {})
                self.client.token = ""
                raise ValueError("Use a faculty account here. Students use the browser dashboard.")
            self.password.clear()
            self.tabs.setTabEnabled(self.account_index, True)
            self.tabs.setTabEnabled(0, False)
            if user["must_change_password"]:
                self.tabs.setCurrentIndex(self.account_index)
                QMessageBox.information(self, "Change password", "Change your initial password to unlock the forms.")
            else:
                self.unlock_forms()
        except ValueError as error:
            QMessageBox.warning(self, "Sign in", str(error))

    def unlock_forms(self):
        for index in range(1, self.account_index):
            self.tabs.setTabEnabled(index, True)
        self.refresh_records()
        self.tabs.setCurrentIndex(1)

    def refresh_records(self):
        try:
            data = self.client.request("records")
            marks = []
            for user in data["users"]:
                if user["role"] == "student":
                    from urllib.parse import urlencode
                    marks.extend(self.client.request("records?" + urlencode({"student_id": user["username"]}))["marks"])
            data["marks"] = marks
            for form in self.forms.values():
                form.refresh(data)
        except ValueError as error:
            QMessageBox.warning(self, "Refresh", str(error))

    def change_password(self):
        try:
            if self.new_password.text() != self.confirm_password.text():
                raise ValueError("Passwords do not match.")
            self.client.request("password", {"old_password": self.old_password.text(), "new_password": self.new_password.text()})
            for field in (self.old_password, self.new_password, self.confirm_password):
                field.clear()
            self.unlock_forms()
            QMessageBox.information(self, "Password", "Password changed.")
        except ValueError as error:
            QMessageBox.warning(self, "Password", str(error))

    def sign_out(self):
        try:
            self.client.request("logout", {})
        except ValueError:
            pass
        self.client.token = ""
        for index in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(index, False)
        self.tabs.setTabEnabled(0, True)
        self.tabs.setCurrentIndex(0)
        for form in self.forms.values():
            form.refresh({})

    def closeEvent(self, event):
        if self.client.token:
            self.sign_out()
        event.accept()


def main():
    app = QApplication(sys.argv)
    configure_font(app)
    window = FacultyWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
