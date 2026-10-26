# Student Growth Planner

A local college project with separate faculty and student accounts. Start with your own records: the application does not seed students, marks, clubs, or activities.

The repository contains source code and tests. Local student records, account notes, database backups, installed environments, reports, and presentations are excluded from Git. A fresh clone starts with an empty database; create the first faculty account and enter your own records.

The browser interface uses a light sage and forest-green theme, with a dedicated welcome screen, account sidebar, summary cards, and responsive forms. Presentation helpers are in `growth_planner/theme.py` and styles are in `growth_planner/styles.css`.

## Start on this computer

After installing the requirements below, double-click `Start-StudentGrowthPlanner.bat`, then open http://127.0.0.1:8501. Keep its command window open. A fresh database offers first faculty setup; an existing local database keeps its saved accounts and records.

The Windows launcher first tries the project's virtual environment. On the development computer it can also use the available bundled Python and local packages.

For the optional faculty desktop interface:

1. Start `Start-API.bat` and leave it running.
2. Start `Start-FacultyDesktop.bat`.
3. Sign in with a faculty account created in the browser.

The Streamlit browser works directly with the shared service/database; it does not require Flask to be running. The PyQt desktop app sends JSON requests to Flask on port 5000. All components use the same SQLite database.

To stop: close the desktop window and press Ctrl+C in each server command window. Closing a browser tab alone does not stop its server.

## Install on another computer

Install Python 3.12 or newer. Clone the project and install its requirements in PowerShell:

```powershell
git clone https://github.com/Pawansaisukhesh2530/studyplanner.git
cd studyplanner
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_project.py browser
```

Create a fresh virtual environment on that computer; virtual environments copied from another machine may contain invalid paths. If a copied `.venv` exists, rename it before creating the new environment.

Use `run_project.py api`, `run_project.py desktop`, or `run_project.py test` in place of `browser` for those components. Alternatively use the provided Windows launchers.

## Enter your data in this order

1. Create the first faculty account and sign in.
2. Accounts and subjects → Accounts: create student accounts with initial passwords.
3. Subjects: add your subjects and pass thresholds.
4. Enrolments: connect students to their subjects.
5. Marks and Assignments: enter academic records.
6. Clubs and events: enter your college's club profiles and events.
7. College calendar: enter actual holidays/closures from your college notice.
8. Sign out. Sign in as a student, change the initial password, and explore the student pages.

Use separate browser profiles or private windows if you want faculty and student sessions open simultaneously.

## Data and backups

Real application data is created at `data/student_growth.db`. Keep this file private. Faculty can download a binary SQLite backup from Backup and logs. To restore, stop all components and double-click `Restore-Backup.bat`; follow the password and confirmation prompts. Restore creates a safety backup in `data/backups/` and clears all login sessions.

Obsolete Version 1 code, fictional sample files, and temporary development assets have been removed. `data/student_growth.db` is the application's database. Tests create their own temporary records and do not seed this database.

## CSV marks format

Download the empty template on the Marks page. Required columns:

```csv
student_id,course_code,assessment,assessment_date,score,max_score
```

Use existing account IDs and subject codes, and enrol the student first. Dates use YYYY-MM-DD. The same student, subject, assessment name, and date updates the existing result. An invalid row cancels the complete import. No filled example dataset is needed.

## What is included

Faculty/student authentication; account and subject editing; enrolments; marks entry/correction and CSV import; assignments and student completion; study tasks; academic analysis/charts; comparable assessment rankings; editable club profiles; explainable matching; saved interests/goals; self-reported participation status; events; personal timed study sessions; clash checks; completed activities; CSV/XML reports; text audit-log export; binary backup and validated offline restore; Flask API; PyQt faculty forms.

External holiday lookup uses Nager.Date. Its live supported-country list did not include India during verification on 25 October 2026. The app reports unsupported countries and network failures rather than inventing dates. Use the faculty-entered college calendar for your actual Indian college holidays. Regional/college closures are not guaranteed by a public API.

This is a local semester project. Assignment completion and club status are self-reported. Faculty are trusted college coordinators. The pass threshold is configurable; analytics are planning summaries rather than official university grades. No email sending, public hosting, automatic certificates, or file-upload assignment grading is included.

## Learn and use the project

- `USER_GUIDE.md`: detailed screen/button walkthrough.
- `CODE_GUIDE.md`: what function runs for each action and how records flow.
- `SEMESTER_MAPPING.md`: connections to your class exercises and viva explanations.
- `REQUIREMENTS_CHECKLIST.md`: implementation and verification evidence.
- Local PDF/PPTX submission files are retained under `outputs/submission/` and are intentionally excluded from GitHub.

## Verification

```powershell
.\Run-Project.bat test
```

Tests create isolated temporary databases under `tmp/`; they do not insert test records into the application database. Browser/desktop tests need local loopback networking. Streamlit may print missing ScriptRunContext warnings from the test harness; check the final test result.
