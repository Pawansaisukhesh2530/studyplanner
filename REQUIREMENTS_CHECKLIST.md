# Completion evidence

Verified on 26 October 2026, including the visual interface refresh. The automated suite passed **19 tests**. Run `Run-Project.bat test` to reproduce the checks. All tests cover the current application and use isolated temporary records; no test depends on Version 1 sample files.

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Faculty/student roles and private records | Planner._actor, _target; app.main | Service/API tests reject faculty actions by students and cross-student reads/edits. |
| Empty default installation | database.initialize_database; setup_faculty | Fresh temporary databases contain no college records and setup_needed is True. Browser setup button tested. Local records are excluded from the repository. |
| User-entered records | Planner methods; dataset_notice | Locally entered academic/campus records, matching, schedules, activities, and XML reports were checked. No database or account credentials are distributed with the source. |
| Real accounts/profile editing | save_user; faculty_accounts | Browser and Qt account saves tested; account IDs and existing roles remain stable. |
| Password handling and sessions | security.py; Planner account methods | Salted hashes; initial-change gate and logout tested; reset/expiry checked in shared service; no hashes/tokens in student snapshots. |
| Courses and editable enrolments | save_course; enrol_student(active) | Browser/desktop entry; enrolment removal hides current assignments while preserving history. |
| Marks entry, correction, persistence | save_mark | Browser save, Qt save/correction, service restart checks. |
| Validated CSV import | import_marks | Invalid later row rolls back earlier writes; unenrolled students and invalid scores rejected. |
| Assignments and completion | save_assignment; set_assignment_completion | Browser creates assignment and marks it complete; faculty completion query and Qt assignment save checked. |
| Personal study tasks | save_task | Browser save, service edit to Done, and ownership checks. |
| Academic charts and summaries | analyse_marks; academic_progress | Known-average tests; every role page renders with entered records; empty state tested. |
| Variation, pass groups, comparable rankings | analyse_marks; assessment_ranking | NumPy mean/std and thresholds inspected; comparison grouping/ranking tested. Class table shows percentage/result. |
| Editable clubs and responsibilities | save_club | Qt club save reaches live API/SQLite; browser form renders. |
| Interests/goals/time and explained matching | save_preferences; recommend_clubs | Preference persistence/normalization checked; ranking/reasons tested; populated student page renders. |
| Personal club status | set_membership | Interested status saved; schedule uses selected clubs; official admission is not implied. |
| Events and personal timed study sessions | save_event; save_study_session | Qt event save; date/time validation and student ownership checks. |
| Combined schedule and clashes | reports.schedule | Overlaps detected, adjacent endpoints excluded, date-only deadlines separate. |
| Actual participation/hours/skills | save_activity | Linked activity saved and totals checked; cross-student edits rejected. Future date/event checks inspected. |
| College holiday calendar | save_college_holiday; remove_college_holiday | Save/correct/remove tests; browser page render; schedule warnings. |
| Real external holiday API | holidays.fetch_holidays | Live Austria 2026 returned 20 holidays. India correctly reported unsupported. Region-filtering and offline behavior tested. |
| CSV/XML exports and summaries | reports.csv_report, xml_report | XML parsed for correct student/no password; empty CSV headers read back; XML academic/activity summaries parsed. |
| Text audit logs | Planner._audit; audit_text | Audit entries checked in restore test; downloadable quoted text; no password/token logging. |
| Binary backup and validated restore | backup.py; restore_backup.py | Consistent round trip, safety backup, cleared sessions, corrupt-file rejection, records preserved on rejection. |
| Flask REST API | api.create_app | HTTP account/marks flow and error/permission tests; live desktop integration. |
| PyQt faculty forms | FacultyWindow; RecordForm | Actual Qt buttons cover accounts, courses, enrolments, marks, assignments, clubs, events, correction, logout. The empty club form was visually inspected during implementation. |
| Simple semester-aligned techniques | functions, classes, loops, regex, PyQt signals, Flask routes, Pandas/NumPy, file handling, exceptions | Reference exercise files read without changes; SEMESTER_MAPPING.md points to actual project code. |
| Windows launchers | Run-Project.bat and component launchers | Actual browser launcher starts localhost server; health endpoint returns ok. Copied environment path issue handled with local runtime fallback. |
| Detailed usage/function documentation | README, USER_GUIDE, CODE_GUIDE, SEMESTER_MAPPING | Screen/button behavior, handlers, service functions, tables, formulas, setup, shutdown, restore, and common errors documented. |

## Explicit product boundaries

This is a local single-college semester application. Faculty are trusted coordinators. Assignment completion and club status are self-reported. No public deployment, automatic grading, email delivery, or certificate verification is implied.

The holiday service did not list India during live verification. The app reports this and supports real faculty-entered college calendar dates. External national/regional data is advisory and may omit college closures. [Holiday API reference](https://nagerholidays.com/api).

Obsolete Version 1 code and sample data have been removed. Both removed historical databases were checked against the fictional sample CSVs and contained only those sample records. The current application database is preserved, and tests never insert records into it.

Restore is an offline maintenance action: stop all components, authenticate current faculty, and type RESTORE. It replaces records and makes a safety backup first.

## Repeat verification

Run `Run-Project.bat test` from this directory. The tests require localhost networking for the browser harness and desktop/API integration. The source files also passed compilation. Desktop save signals were tested against a live API; its long club form was rendered offscreen and visually inspected.
