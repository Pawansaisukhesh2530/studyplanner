"""Authenticated local JSON API used by the faculty desktop app."""

import inspect
import os
import sqlite3

from flask import Flask, jsonify, request

from growth_planner.database import DATABASE_FILE
from growth_planner.service import AccessError, Planner


# Explicit routes: a client cannot invoke arbitrary Python attributes.
OPERATIONS = {
    "accounts": "save_user", "courses": "save_course", "enrolments": "enrol_student",
    "marks": "save_mark", "marks/import": "import_marks", "assignments": "save_assignment",
    "assignments/completion": "set_assignment_completion", "tasks": "save_task",
    "preferences": "save_preferences", "clubs": "save_club", "memberships": "set_membership",
    "events": "save_event", "study-sessions": "save_study_session", "activities": "save_activity",
    "password": "change_password", "logout": "logout",
    "college-holidays": "save_college_holiday", "college-holidays/remove": "remove_college_holiday",
}


def create_app(database_file=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 3_000_000
    planner = Planner(database_file or os.environ.get("GROWTH_PLANNER_DB", str(DATABASE_FILE)))

    def token():
        header = request.headers.get("Authorization", "")
        return header[7:] if header.startswith("Bearer ") else ""

    def body():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("Send a JSON object.")
        return value

    def invoke(function, *args):
        payload = body()
        # Bind before calling so invalid/missing arguments become useful client errors.
        try:
            inspect.signature(function).bind(*args, **payload)
        except TypeError as error:
            raise ValueError("Invalid fields: " + str(error))
        return function(*args, **payload)

    @app.errorhandler(AccessError)
    def access_error(error):
        return jsonify(error=str(error)), 403

    @app.errorhandler(ValueError)
    @app.errorhandler(sqlite3.IntegrityError)
    def input_error(error):
        return jsonify(error=str(error)), 400

    @app.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/api/status")
    def status():
        return jsonify(setup_needed=planner.setup_needed())

    @app.post("/api/setup")
    def setup():
        return jsonify(message=invoke(planner.setup_faculty))

    @app.post("/api/login")
    def login():
        return jsonify(token=invoke(planner.login))

    @app.get("/api/me")
    def me():
        return jsonify(planner.current_user(token()))

    @app.get("/api/records")
    def records():
        return jsonify(planner.snapshot(token(), request.args.get("student_id")))

    @app.get("/api/audit")
    def audit():
        return app.response_class(planner.audit_text(token()), mimetype="text/plain")

    @app.get("/api/class-marks")
    def class_marks():
        return jsonify(planner.class_marks(token()))

    @app.post("/api/<path:operation>")
    def mutate(operation):
        if operation not in OPERATIONS:
            return jsonify(error="Unknown operation."), 404
        result = invoke(getattr(planner, OPERATIONS[operation]), token())
        return jsonify(result=result)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
