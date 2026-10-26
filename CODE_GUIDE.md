# Code guide: what runs when you click

## Start reading here

Read `app.py` → `main()`, then `growth_planner/ui.py`, then the corresponding method on `Planner` in `growth_planner/service.py`. Finally inspect `database.py` for the table being updated.

The browser path is:

`click → UI function → perform() → Planner method → validation and permission check → SQLite transaction → Streamlit rerun → fresh snapshot → updated screen`

Streamlit executes the page again after interactions. Form fields are submitted together when their Save button is clicked. `st.session_state` stores the login token and one success notice across reruns. `perform()` catches validation errors; successful mutations show a notice and refresh the page. `Planner.snapshot()` reads current records instead of trusting cached display data.

The desktop path is:

`Qt button clicked signal → RecordForm.save_record() → ApiClient.request() → HTTP JSON → Flask route in api.py → the same Planner method → SQLite → JSON response → Saved dialog → refresh_records()`

The desktop and browser share rules and tables. The browser does not make an unnecessary HTTP request to its own local API.

## File responsibilities

| File | Responsibility |
| --- | --- |
| app.py | Configure Streamlit, select the database, check login, dispatch by role. |
| growth_planner/ui.py | Forms, tables, buttons, charts, page navigation, downloads. |
| growth_planner/theme.py | Brand, sidebar profile, welcome panel, status badges, empty states, and consistent submit buttons. |
| growth_planner/styles.css | Sage/forest colour palette, cards, responsive spacing, navigation, forms, and chart styling. |
| growth_planner/service.py | Accounts, academic records, assignments, tasks, clubs, schedules, activities, permissions. |
| growth_planner/database.py | SQLite schema, connection lifetime, transactions, row-to-dictionary conversion. |
| growth_planner/validation.py | Required text, IDs, emails, finite numbers, dates, time ranges, tags. |
| growth_planner/security.py | Password hashing/checking and token hashing. |
| growth_planner/reports.py | Pandas/NumPy analysis, comparable ranks, schedule clashes, CSV/XML output. |
| growth_planner/matching.py | Explainable interest/goal/time club matching. |
| growth_planner/holidays.py | Real HTTP holiday requests, country coverage checks, region filtering, friendly failures. |
| growth_planner/backup.py | SQLite backup, structural validation, safety backup, restore. |
| api.py | Flask application factory, explicit operation allowlist, JSON endpoints, error responses. |
| faculty_desktop.py | PyQt widgets, signals, form selection/editing, API client. |
| restore_backup.py | Faculty-authenticated maintenance prompts for an offline restore. |
| run_project.py | Locate available local packages and start browser/API/desktop/restore/tests. |
| tests/ | Temporary-database service, browser, API, desktop, backup, and holiday tests. |

The folder contains the current application modules. Obsolete Version 1 modules and sample datasets have been removed; `tests/test_core.py` checks the current matching, analytics, exports, and scheduling functions without depending on demo files.

## Every browser action mapped to code

UI handlers below are in `growth_planner/ui.py`; Planner methods are in `growth_planner/service.py` unless otherwise specified.

| Screen/action | UI handler | Function doing the work | Saved/read result |
| --- | --- | --- | --- |
| Initial Create faculty account | login_screen | setup_needed, setup_faculty | users row and audit entry; no seed records. |
| Sign in | login_screen | login | Expiring session token; UI stores token. |
| Sign out | app.main | logout | Deletes current sessions row; clears browser state. |
| Change password | password_screen | change_password | Replaces hash, clears initial-password flag, revokes other sessions. |
| Page selection | faculty_home / student_home | snapshot | Reloads permitted records for the chosen view. |
| Add new / choose existing | choose_record | No write | Selects a dictionary used to fill a form. |
| Save account | faculty_accounts | save_user | Creates/edits users; optional password reset revokes target sessions. |
| Save subject | faculty_accounts | save_course | Upserts courses by code. |
| Enrol student | faculty_accounts | enrol_student(active=True) | Adds enrolments link if missing. |
| Remove enrolment | faculty_accounts | enrol_student(active=False) | Removes link; historical marks/completions retained. |
| Select student on Marks | faculty_marks | snapshot(student_id) | Reads that student's subjects and marks; faculty-only cross-student access. |
| Save marks | faculty_marks | save_mark → _mark_values → _write_mark | Validates enrolment and score, inserts or updates unique assessment. |
| Download empty marks template | faculty_marks | st.download_button | Downloads a header; no database change. |
| Choose CSV file | faculty_marks | st.file_uploader | Holds uploaded bytes until Import is clicked. |
| Import marks | faculty_marks | import_marks | Validates/writes in one transaction; invalid row rolls everything back. |
| Class assessment comparison | faculty_marks | class_marks → reports.assessment_ranking | Groups comparable assessments and computes tied ranks. |
| Save assignment | faculty_assignments | save_assignment | Adds or edits assignments, preserving existing subject. |
| Completion table | faculty_assignments | snapshot → completions query | Joins assignments with current enrolments and saved statuses. |
| Save club | faculty_clubs | save_club | Upserts profile and normalized matching tags. |
| Save event | faculty_clubs → time_fields | save_event | Validates time order and club; adds/edits event. |
| Save college holiday | faculty_home, College calendar branch | save_college_holiday | Upserts official college calendar date. |
| Remove college holiday | faculty_home, College calendar branch | remove_college_holiday | Removes that date after UI confirmation. |
| Select student report | faculty_home | snapshot(student_id), academic_progress | Reads permitted academic and participation data. |
| Prepare database backup | faculty_home | backup.create_backup | Consistent SQLite snapshot, with sessions removed. |
| Download prepared backup | faculty_home | st.download_button | Downloads previously prepared bytes. |
| Download audit log | faculty_home | audit_text | Exports quoted tab-separated audit metadata. |
| Academic progress | academic_progress | reports.analyse_marks | Calculates percentages, averages, variation and subject/date tables. |
| Assessment records expander | academic_progress | table | Displays calculated records; no write. |
| Mark complete / Mark open | student_work | set_assignment_completion | Checks enrolment and upserts own completion timestamp/null. |
| Save study task | student_work | save_task | Creates/edits only the signed-in student's task and status. |
| Save preferences | student_clubs | save_preferences | Saves normalized interests/goals and weekly availability. |
| Suggested club cards | student_clubs | matching.recommend_clubs | Scores/sorts clubs using saved preferences and readable reasons. |
| Save club status | student_clubs | set_membership | Upserts Interested/Participating, or removes own status. |
| Combined schedule | student_schedule | reports.schedule | Combines selected-club events and own sessions; detects overlaps; lists open deadlines. |
| Save study session | student_schedule → time_fields | save_study_session | Creates/edits own timed study plan. |
| Look up holidays | student_schedule | holidays.fetch_holidays → get_json | Reads external API, checks country and scope; no database write. |
| Save completed activity | student_activities | save_activity | Validates actual date/hours, optional event, and ownership; saves participation. |
| Download marks CSV | download_reports | reports.csv_report | Exports own/selected permitted student's marks. |
| Download activity CSV | download_reports | reports.csv_report | Exports actual participation. |
| Download complete XML report | download_reports | reports.xml_report | Builds XML from permitted snapshot sections. |

Download buttons do not alter records. Entering text or selecting a record does not save a form. Save/Import/Completion buttons are the mutations. Invalid input displays an error rather than a success notice.

## Database relationships

`users` stores faculty and students, distinguished by role. The username is the stable account ID. `courses` stores subjects and pass thresholds. `enrolments` links a student to a course.

`marks` links a student and course. Its unique key is student + course + assessment name + assessment date. `assignments` belongs to a course; `assignment_status` links one assignment and student with an optional completion timestamp. `tasks` belongs directly to a student.

`clubs` stores profiles and matching tags. `memberships` links students to clubs with self-reported interest/participation status. `events` belongs to a club. `study_sessions` belongs to a student. `activities` links student and club and optionally an event. `college_holidays` stores faculty-entered dates. `audit_log` records action metadata. `sessions` links hashed login tokens to users and UTC expiry times. `app_meta` records the schema version.

`open_database()` is a context manager: open connection, enable foreign keys, yield it, commit on success or roll back on error, always close. Queries pass values with `?` placeholders. SQL table names in fixed loops come from code-controlled lists, not user input.

## Permissions and password handling

`_actor()` hashes the supplied token, looks up an unexpired session, checks role when required, and blocks normal operations until an initial password has changed. Each protected method calls it; the UI hiding a button is not the security boundary.

`_target()` allows faculty to choose students and rejects a student asking for a different student ID. Student save methods derive the owner from the session instead of accepting a client-supplied owner. Updating tasks, study sessions, and activities includes `WHERE id=? AND student_id=?` and checks the affected row count.

`hash_password()` uses PBKDF2-HMAC-SHA256, a random salt, and 300,000 iterations. `check_password()` compares hashes using `hmac.compare_digest`. Passwords are not stored in plaintext. Login tokens are random; only token hashes are saved in SQLite. Initial-password change, reset, logout, expiration, and restore have explicit session behavior.

## Calculations explained simply

- Assessment percentage: score divided by maximum, multiplied by 100.
- Overall average: NumPy mean of unrounded assessment percentages; one decimal at display.
- Subject average: Pandas grouping by subject code/name; simple assessment mean.
- Date trend: average percentage among assessments recorded on each date. It is not a cumulative average.
- Variation: NumPy population standard deviation of assessment percentages.
- Pass/below-threshold: percentage or subject average compared with the configured subject threshold; an average is not an official final result.
- Assessment rank: Pandas rank within identical course/name/date/maximum groups. Equal scores use the same minimum rank.
- Club match: 3 × shared interests + 2 × shared goals + 2 if time fits. Higher score first; club name breaks ties.
- Clash: two intervals overlap when each begins before the other ends. Exactly touching endpoints are allowed. Date-only deadlines stay outside the timed comparison.

## Flask routes

`create_app()` lets tests provide a temporary database instead of touching real records. `OPERATIONS` explicitly maps HTTP paths to allowed service methods.

| Request | Behavior |
| --- | --- |
| GET /api/status | Whether first faculty setup is needed. |
| POST /api/setup | Initial faculty setup once only. |
| POST /api/login | Returns an opaque token. |
| GET /api/me | Public fields for the signed-in account. |
| GET /api/records?student_id=ID | Authorized snapshot; only faculty can request another student. |
| GET /api/class-marks | Faculty-only comparable assessment data. |
| GET /api/audit | Faculty-only text audit export. |
| POST /api/accounts, courses, enrolments, marks, assignments, clubs, events | Faculty record entry/editing. |
| POST /api/marks/import | Faculty CSV text import. |
| POST /api/college-holidays, college-holidays/remove | Faculty calendar management. |
| POST /api/assignments/completion, tasks, preferences, memberships, study-sessions, activities | Own student workflows. |
| POST /api/password, logout | Password/session actions. |

Protected requests use `Authorization: Bearer TOKEN`. POST bodies are JSON objects using the corresponding Planner method's parameter names, excluding token. Unknown fields/missing arguments return 400. Access errors return 403. Unknown operations return 404. Responses disable caching. Local launch binds to 127.0.0.1, with debug off.

## Desktop functions

`FacultyWindow` creates the login, record tabs, and Account tab. `sign_in()` calls login/me, rejects student roles, and requires initial password changes. `unlock_forms()` enables record pages. `refresh_records()` retrieves shared lists plus student marks and calls each form's `refresh()`.

`RecordForm` creates simple widgets from the `FORMS` field definitions. `load_record()` fills fields and disables stable identifiers while editing. `save_record()` reads widgets, converts numeric fields, adds an assignment/event ID for edits, calls the allowed API route, shows the result, and refreshes. The schema/configuration describes fields; it does not bypass shared rules.

`ApiClient.request()` sends JSON with urllib and reports HTTP/network errors. `change_password()` calls the API, clears password widgets, and unlocks forms. `sign_out()` revokes the token, clears records, and disables forms. `closeEvent()` signs out when the window closes.

## Backup and restore

`create_backup()` authorizes faculty, logs the action, uses SQLite's backup API, removes sessions from the copy, validates it, and returns bytes. Temporary connections are explicitly closed so Windows does not keep files locked.

`validate_backup()` checks readable SQLite data, integrity, exact expected schema (including no unexpected triggers/views), foreign-key consistency, schema version, and a faculty account. `restore_backup()` authenticates current faculty, validates the incoming backup, saves a safety copy, copies using SQLite's transactional backup API, clears sessions, and logs restoration. The maintenance utility asks for explicit typed confirmation and requires all app components stopped.

## Suggested code-reading order for your viva

1. `app.main()` and `ui.login_screen()`.
2. `Planner.setup_faculty()`, `login()`, `_actor()`, `_target()`.
3. `faculty_marks()` → `save_mark()` → `_mark_values()` → `_write_mark()`.
4. `analyse_marks()` and `recommend_clubs()`.
5. `student_work()`, `save_task()`, `set_assignment_completion()`.
6. `schedule()`, `save_event()`, `save_activity()`.
7. `api.create_app()` and `RecordForm.save_record()`.
8. CSV/XML, holiday request, audit log, backup/restore.
9. The workflow tests showing that these functions work together.
