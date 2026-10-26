"""Application rules. Every public operation checks the signed-in account."""

import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
import secrets
import sqlite3

from growth_planner.database import DATABASE_FILE, initialize_database, open_database, rows
from growth_planner.security import check_password, hash_password, token_digest
from growth_planner.validation import calendar_date, email_address, identifier, number, required, tags, time_range


class AccessError(ValueError):
    """The requested action is not allowed for this account."""


class Planner:
    def __init__(self, database_file=DATABASE_FILE):
        self.database_file = Path(database_file)
        initialize_database(self.database_file)

    def setup_needed(self):
        with open_database(self.database_file) as db:
            return db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0

    def dataset_notice(self):
        """Explain an explicitly imported practice dataset, when one is present."""
        with open_database(self.database_file) as db:
            notice = db.execute("SELECT value FROM app_meta WHERE key='dataset_notice'").fetchone()
            return notice["value"] if notice else ""

    def _audit(self, db, username, action, record_key):
        # Only action metadata is logged: never passwords, tokens, or submitted work.
        db.execute("INSERT INTO audit_log(recorded_at,username,action,record_key) VALUES (?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), username, action, str(record_key)))

    def setup_faculty(self, username, name, email, password):
        username = identifier(username, "Faculty ID")
        name = required(name, "Name")
        email = email_address(email)
        password_hash = hash_password(password)
        with open_database(self.database_file) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                raise AccessError("Setup is already complete. Sign in with a faculty account.")
            db.execute("INSERT INTO users(username,name,email,role,password_hash,must_change_password) VALUES (?,?,?,?,?,0)",
                       (username, name, email, "faculty", password_hash))
            self._audit(db, username, "initial faculty setup", username)
        return "Faculty account created. You can now sign in."

    def login(self, username, password):
        if not isinstance(username, str):
            raise AccessError("Incorrect ID or password.")
        with open_database(self.database_file) as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
            if user is None or not check_password(password, user["password_hash"]):
                raise AccessError("Incorrect ID or password.")
            token = secrets.token_urlsafe(32)
            expires = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (datetime.now(timezone.utc).isoformat(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?)", (token_digest(token), user["username"], expires))
            self._audit(db, user["username"], "login", user["username"])
        return token

    def _actor(self, db, token, faculty=False, allow_password_change=False):
        if not isinstance(token, str) or not token:
            raise AccessError("Please sign in.")
        user = db.execute(
            "SELECT users.* FROM sessions JOIN users USING(username) WHERE token_hash=? AND expires_at>?",
            (token_digest(token), datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        if user is None:
            raise AccessError("Your session expired. Please sign in again.")
        if faculty and user["role"] != "faculty":
            raise AccessError("Only faculty can perform this action.")
        if user["must_change_password"] and not allow_password_change:
            raise AccessError("Change your initial password before continuing.")
        return dict(user)

    def current_user(self, token):
        with open_database(self.database_file) as db:
            user = self._actor(db, token, allow_password_change=True)
        del user["password_hash"]
        return user

    def logout(self, token):
        with open_database(self.database_file) as db:
            if isinstance(token, str):
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_digest(token),))
        return "Signed out."

    def change_password(self, token, old_password, new_password):
        password_hash = hash_password(new_password)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, allow_password_change=True)
            if not check_password(old_password, actor["password_hash"]):
                raise AccessError("Current password is incorrect.")
            if check_password(new_password, actor["password_hash"]):
                raise ValueError("Choose a different new password.")
            db.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE username=?",
                       (password_hash, actor["username"]))
            db.execute("DELETE FROM sessions WHERE username=? AND token_hash<>?", (actor["username"], token_digest(token)))
            self._audit(db, actor["username"], "password changed", actor["username"])
        return "Password changed."

    def save_user(self, token, username, name, email, role="student", initial_password=""):
        username = identifier(username, "Account ID")
        name = required(name, "Name")
        email = email_address(email)
        if role not in ("student", "faculty"):
            raise ValueError("Choose student or faculty.")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            existing = db.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
            if existing:
                if existing["role"] != role:
                    raise ValueError("An existing account's role cannot be changed.")
                db.execute("UPDATE users SET name=?, email=? WHERE username=?", (name, email, username))
                if initial_password:
                    if username == actor["username"]:
                        raise ValueError("Use Change password for your own account.")
                    db.execute("UPDATE users SET password_hash=?,must_change_password=1 WHERE username=?",
                               (hash_password(initial_password), username))
                    db.execute("DELETE FROM sessions WHERE username=?", (username,))
            else:
                db.execute("INSERT INTO users(username,name,email,role,password_hash) VALUES (?,?,?,?,?)",
                           (username, name, email, role, hash_password(initial_password)))
            self._audit(db, actor["username"], "save account", username)
        return "Account saved. A supplied initial/reset password must be changed at next login."

    def save_course(self, token, code, name, pass_percentage=40):
        code = identifier(code, "Subject code")
        name = required(name, "Subject name")
        threshold = number(pass_percentage, "Pass percentage", 0, 100)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            db.execute("INSERT INTO courses VALUES (?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,pass_percentage=excluded.pass_percentage",
                       (code, name, threshold))
            self._audit(db, actor["username"], "save subject", code)
        return "Subject saved."

    def _student(self, db, student_id):
        student_id = identifier(student_id, "Student ID")
        if not db.execute("SELECT 1 FROM users WHERE username=? AND role='student'", (student_id,)).fetchone():
            raise ValueError("Student account does not exist.")
        return student_id

    def _course(self, db, course_code):
        code = identifier(course_code, "Subject code")
        if not db.execute("SELECT 1 FROM courses WHERE code=?", (code,)).fetchone():
            raise ValueError("Subject does not exist.")
        return code

    def _target(self, db, actor, student_id=None):
        target = self._student(db, student_id or actor["username"])
        if actor["role"] == "student" and target != actor["username"]:
            raise AccessError("You can access only your own records.")
        return target

    def enrol_student(self, token, student_id, course_code, active=True):
        if not isinstance(active, bool):
            raise ValueError("Enrolment active must be true or false.")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            student_id = self._student(db, student_id)
            code = self._course(db, course_code)
            if active:
                db.execute("INSERT OR IGNORE INTO enrolments VALUES (?,?)", (student_id, code))
            else:
                db.execute("DELETE FROM enrolments WHERE student_id=? AND course_code=?", (student_id, code))
            self._audit(db, actor["username"], "enrol student" if active else "remove enrolment", student_id + ":" + code)
        return "Student enrolled in subject." if active else "Enrolment removed. Existing marks and completion history are kept."

    def save_college_holiday(self, token, holiday_date, name):
        holiday_date = calendar_date(holiday_date)
        name = required(name, "Holiday name")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            db.execute("INSERT INTO college_holidays VALUES (?,?) ON CONFLICT(holiday_date) DO UPDATE SET name=excluded.name", (holiday_date, name))
            self._audit(db, actor["username"], "save college holiday", holiday_date)
        return "College holiday saved."

    def remove_college_holiday(self, token, holiday_date):
        holiday_date = calendar_date(holiday_date)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            db.execute("DELETE FROM college_holidays WHERE holiday_date=?", (holiday_date,))
            self._audit(db, actor["username"], "remove college holiday", holiday_date)
        return "College holiday removed."

    def class_marks(self, token):
        with open_database(self.database_file) as db:
            self._actor(db, token, faculty=True)
            return rows(db, "SELECT m.*,u.name,c.name AS subject,c.pass_percentage FROM marks m JOIN users u ON u.username=m.student_id JOIN courses c ON c.code=m.course_code ORDER BY course_code,assessment,assessment_date,score DESC")

    def _mark_values(self, db, record):
        student = self._student(db, record["student_id"])
        code = self._course(db, record["course_code"])
        if not db.execute("SELECT 1 FROM enrolments WHERE student_id=? AND course_code=?", (student, code)).fetchone():
            raise ValueError("Enrol this student in the subject before entering marks.")
        assessment = required(record["assessment"], "Assessment name")
        when = calendar_date(record["assessment_date"], "Assessment date")
        if date.fromisoformat(when) > date.today():
            raise ValueError("Assessment marks cannot be recorded for a future date.")
        maximum = number(record["max_score"], "Maximum score", 0.01)
        score = number(record["score"], "Score", 0, maximum)
        return student, code, assessment, when, score, maximum

    def _write_mark(self, db, values):
        existing = db.execute("SELECT id FROM marks WHERE student_id=? AND course_code=? AND assessment=? AND assessment_date=?", values[:4]).fetchone()
        db.execute("""INSERT INTO marks(student_id,course_code,assessment,assessment_date,score,max_score)
                      VALUES (?,?,?,?,?,?) ON CONFLICT(student_id,course_code,assessment,assessment_date)
                      DO UPDATE SET score=excluded.score,max_score=excluded.max_score""", values)
        return bool(existing)

    def save_mark(self, token, student_id, course_code, assessment, assessment_date, score, max_score):
        record = dict(student_id=student_id, course_code=course_code, assessment=assessment,
                      assessment_date=assessment_date, score=score, max_score=max_score)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            values = self._mark_values(db, record)
            updated = self._write_mark(db, values)
            self._audit(db, actor["username"], "correct marks" if updated else "add marks", ":".join(values[:4]))
        return "Marks corrected." if updated else "Marks saved."

    def import_marks(self, token, csv_text):
        if not isinstance(csv_text, str) or len(csv_text) > 2_000_000:
            raise ValueError("CSV must be text and at most 2 MB.")
        reader = csv.DictReader(StringIO(csv_text.lstrip('\ufeff')))
        fields = {"student_id", "course_code", "assessment", "assessment_date", "score", "max_score"}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError("Required columns: " + ",".join(sorted(fields)))
        added = updated = 0
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            for line, record in enumerate(reader, 2):
                try:
                    values = self._mark_values(db, record)
                except (ValueError, TypeError, KeyError) as error:
                    raise ValueError(f"CSV row {line}: {error}")
                if self._write_mark(db, values):
                    updated += 1
                else:
                    added += 1
            if not added + updated:
                raise ValueError("CSV has no assessment rows.")
            self._audit(db, actor["username"], "import marks", f"added={added},updated={updated}")
        return {"added": added, "updated": updated}

    def save_assignment(self, token, course_code, title, instructions, due_date, assignment_id=None):
        title = required(title, "Title")
        instructions = required(instructions, "Instructions", 10000)
        due_date = calendar_date(due_date, "Due date")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            code = self._course(db, course_code)
            if assignment_id is None:
                cursor = db.execute("INSERT INTO assignments(course_code,title,instructions,due_date,created_by) VALUES (?,?,?,?,?)",
                                    (code, title, instructions, due_date, actor["username"]))
                assignment_id = cursor.lastrowid
            else:
                old = db.execute("SELECT course_code FROM assignments WHERE id=?", (assignment_id,)).fetchone()
                if old is None:
                    raise ValueError("Assignment does not exist.")
                if old["course_code"] != code:
                    raise ValueError("An existing assignment's subject cannot be changed.")
                db.execute("UPDATE assignments SET title=?,instructions=?,due_date=? WHERE id=?", (title, instructions, due_date, assignment_id))
            self._audit(db, actor["username"], "save assignment", assignment_id)
        return "Assignment saved. Enrolled students can view it."

    def set_assignment_completion(self, token, assignment_id, completed):
        if not isinstance(completed, bool):
            raise ValueError("Completion must be true or false.")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            assignment = db.execute("SELECT 1 FROM assignments a JOIN enrolments e USING(course_code) WHERE a.id=? AND e.student_id=?", (assignment_id, student)).fetchone()
            if assignment is None:
                raise AccessError("This assignment is not assigned to you.")
            when = datetime.now().isoformat(timespec="seconds") if completed else None
            db.execute("INSERT INTO assignment_status VALUES (?,?,?) ON CONFLICT(assignment_id,student_id) DO UPDATE SET completed_at=excluded.completed_at", (assignment_id, student, when))
            self._audit(db, student, "assignment completion", assignment_id)
        return "Assignment completion updated."

    def save_task(self, token, title, subject, due_date, task_id=None, status="Open"):
        title = required(title, "Task")
        subject = required(subject, "Subject")
        due_date = calendar_date(due_date, "Due date")
        if status not in ("Open", "Done"):
            raise ValueError("Task status must be Open or Done.")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            if task_id is None:
                task_id = db.execute("INSERT INTO tasks(student_id,title,subject,due_date,status) VALUES (?,?,?,?,?)", (student, title, subject, due_date, status)).lastrowid
            else:
                result = db.execute("UPDATE tasks SET title=?,subject=?,due_date=?,status=? WHERE id=? AND student_id=?", (title, subject, due_date, status, task_id, student))
                if result.rowcount != 1:
                    raise AccessError("Task not found in your records.")
            self._audit(db, student, "save task", task_id)
        return "Study task saved."

    def save_preferences(self, token, interests, goals, weekly_hours):
        interests, goals = tags(interests), tags(goals)
        weekly_hours = number(weekly_hours, "Weekly hours", 0, 168)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            db.execute("UPDATE users SET interests=?,goals=?,weekly_hours=? WHERE username=?", (interests, goals, weekly_hours, student))
            self._audit(db, student, "save preferences", student)
        return "Preferences saved."

    def save_club(self, token, club_id, name, category, description, interests, goals, skills, hours_per_week, example_activities, potential_benefit):
        club_id = identifier(club_id, "Club ID")
        values = (club_id, required(name, "Club name"), required(category, "Category"),
                  required(description, "Description and responsibilities", 10000), tags(interests), tags(goals), tags(skills),
                  number(hours_per_week, "Weekly hours", 0.5, 168), required(example_activities, "Typical activities", 10000),
                  required(potential_benefit, "Possible benefits", 10000))
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            db.execute("""INSERT INTO clubs VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(club_id) DO UPDATE SET
                       name=excluded.name,category=excluded.category,description=excluded.description,
                       interests=excluded.interests,goals=excluded.goals,skills=excluded.skills,hours_per_week=excluded.hours_per_week,
                       example_activities=excluded.example_activities,potential_benefit=excluded.potential_benefit""", values)
            self._audit(db, actor["username"], "save club", club_id)
        return "Club saved."

    def set_membership(self, token, club_id, status):
        if status not in ("Interested", "Participating", "Remove"):
            raise ValueError("Choose Interested, Participating or Remove.")
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            self._club(db, club_id)
            if status == "Remove":
                db.execute("DELETE FROM memberships WHERE student_id=? AND club_id=?", (student, club_id))
            else:
                db.execute("INSERT INTO memberships VALUES (?,?,?) ON CONFLICT(student_id,club_id) DO UPDATE SET status=excluded.status", (student, club_id, status))
            self._audit(db, student, "club interest/status", club_id)
        return "Your club status is saved. This is your record, not official admission."

    def _club(self, db, club_id):
        if not db.execute("SELECT 1 FROM clubs WHERE club_id=?", (club_id,)).fetchone():
            raise ValueError("Club does not exist.")

    def save_event(self, token, club_id, title, starts_at, ends_at, location, event_id=None):
        title, location = required(title, "Event title"), required(location, "Location")
        starts_at, ends_at = time_range(starts_at, ends_at)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token, faculty=True)
            self._club(db, club_id)
            if event_id is None:
                event_id = db.execute("INSERT INTO events(club_id,title,starts_at,ends_at,location) VALUES (?,?,?,?,?)", (club_id, title, starts_at, ends_at, location)).lastrowid
            else:
                result = db.execute("UPDATE events SET club_id=?,title=?,starts_at=?,ends_at=?,location=? WHERE id=?", (club_id, title, starts_at, ends_at, location, event_id))
                if result.rowcount != 1:
                    raise ValueError("Event does not exist.")
                if db.execute("SELECT 1 FROM activities WHERE event_id=? AND club_id<>?", (event_id, club_id)).fetchone():
                    raise ValueError("Cannot move an event to another club after participation is recorded.")
            self._audit(db, actor["username"], "save event", event_id)
        return "Event saved."

    def save_study_session(self, token, title, starts_at, ends_at, session_id=None):
        title = required(title, "Session title")
        starts_at, ends_at = time_range(starts_at, ends_at)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            if session_id is None:
                session_id = db.execute("INSERT INTO study_sessions(student_id,title,starts_at,ends_at) VALUES (?,?,?,?)", (student, title, starts_at, ends_at)).lastrowid
            else:
                result = db.execute("UPDATE study_sessions SET title=?,starts_at=?,ends_at=? WHERE id=? AND student_id=?", (title, starts_at, ends_at, session_id, student))
                if result.rowcount != 1:
                    raise AccessError("Study session not found in your records.")
            self._audit(db, student, "save study session", session_id)
        return "Study session saved."

    def save_activity(self, token, club_id, activity_date, description, hours, skills_practised, event_id=None, activity_id=None):
        activity_date = calendar_date(activity_date, "Activity date")
        if date.fromisoformat(activity_date) > date.today():
            raise ValueError("Record activities only after they happen.")
        description = required(description, "What you did", 10000)
        hours = number(hours, "Hours", 0.01, 24)
        skills = tags(skills_practised)
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            student = self._target(db, actor)
            self._club(db, club_id)
            if event_id is not None:
                event = db.execute("SELECT * FROM events WHERE id=? AND club_id=?", (event_id, club_id)).fetchone()
                if event is None:
                    raise ValueError("Choose an event belonging to this club.")
                if datetime.fromisoformat(event["ends_at"]) > datetime.now():
                    raise ValueError("The selected event has not finished yet.")
                if not event["starts_at"][:10] <= activity_date <= event["ends_at"][:10]:
                    raise ValueError("Participation date must fall within the selected event.")
            values = (club_id, event_id, activity_date, description, hours, skills)
            if activity_id is None:
                activity_id = db.execute("INSERT INTO activities(club_id,event_id,activity_date,description,hours,skills_practised,student_id) VALUES (?,?,?,?,?,?,?)", (*values, student)).lastrowid
            else:
                result = db.execute("UPDATE activities SET club_id=?,event_id=?,activity_date=?,description=?,hours=?,skills_practised=? WHERE id=? AND student_id=?", (*values, activity_id, student))
                if result.rowcount != 1:
                    raise AccessError("Activity not found in your records.")
            self._audit(db, student, "save participation", activity_id)
        return "Completed activity saved."

    def snapshot(self, token, student_id=None):
        """Return only the records this account is allowed to read."""
        with open_database(self.database_file) as db:
            actor = self._actor(db, token)
            output = {"clubs": rows(db, "SELECT * FROM clubs ORDER BY name"),
                      "college_holidays": rows(db, "SELECT * FROM college_holidays ORDER BY holiday_date"),
                      "events": rows(db, "SELECT e.*, c.name AS club FROM events e JOIN clubs c USING(club_id) ORDER BY starts_at")}
            if actor["role"] == "faculty":
                output["users"] = rows(db, "SELECT username,name,email,role,must_change_password FROM users ORDER BY role,name")
                output["courses"] = rows(db, "SELECT * FROM courses ORDER BY name")
                output["enrolments"] = rows(db, "SELECT * FROM enrolments ORDER BY student_id,course_code")
                output["all_assignments"] = rows(db, "SELECT * FROM assignments ORDER BY due_date")
                output["completions"] = rows(db, """SELECT a.id AS assignment_id,a.title,e.student_id,s.completed_at
                    FROM assignments a JOIN enrolments e USING(course_code)
                    LEFT JOIN assignment_status s ON s.assignment_id=a.id AND s.student_id=e.student_id
                    ORDER BY a.due_date,e.student_id""")
                if not student_id:
                    return output
            student = self._target(db, actor, student_id)
            profile = dict(db.execute("SELECT username,name,email,interests,goals,weekly_hours FROM users WHERE username=?", (student,)).fetchone())
            output["profile"] = profile
            output["student_courses"] = rows(db, "SELECT c.* FROM courses c JOIN enrolments e ON e.course_code=c.code WHERE e.student_id=? ORDER BY name", (student,))
            output["marks"] = rows(db, "SELECT m.*,c.name AS subject,c.pass_percentage FROM marks m JOIN courses c ON c.code=m.course_code WHERE student_id=? ORDER BY assessment_date,subject", (student,))
            output["assignments"] = rows(db, """SELECT a.*,c.name AS subject,s.completed_at FROM assignments a
                JOIN courses c ON c.code=a.course_code JOIN enrolments e ON e.course_code=a.course_code
                LEFT JOIN assignment_status s ON s.assignment_id=a.id AND s.student_id=e.student_id
                WHERE e.student_id=? ORDER BY a.due_date""", (student,))
            for table in ("tasks", "memberships", "study_sessions"):
                output[table] = rows(db, "SELECT * FROM " + table + " WHERE student_id=?", (student,))
            output["activities"] = rows(db, "SELECT a.*,c.name AS club FROM activities a JOIN clubs c USING(club_id) WHERE student_id=? ORDER BY activity_date DESC", (student,))
            return output

    def audit_text(self, token):
        with open_database(self.database_file) as db:
            self._actor(db, token, faculty=True)
            entries = rows(db, "SELECT * FROM audit_log ORDER BY id")
        # CSV quoting makes user-controlled newlines unambiguous in a text log.
        output = StringIO(newline="")
        writer = csv.writer(output, delimiter='\t')
        writer.writerow(["UTC timestamp", "Account", "Action", "Record"])
        for entry in entries:
            writer.writerow([entry["recorded_at"], entry["username"], entry["action"], entry["record_key"]])
        return output.getvalue()
