# How this project connects to your semester Python work

The semester exercise folder was reviewed without changing its files. The table maps those exercises to the application code.

| Your exercise | Project use | Where to read | Simple viva explanation |
| --- | --- | --- | --- |
| Student_Information_Form.py | QWidget forms, text fields, role combo, layouts, button signals, message boxes | faculty_desktop.py: FacultyWindow, RecordForm | A button's clicked signal calls a method that reads and validates fields. Here the submitted record is saved through the API. |
| PyQtApplicationUsingClass.py; Button_Signal.py | A class creates and groups related GUI widgets and behavior | FacultyWindow.__init__, RecordForm.__init__, save_record | The window is an object. Its methods respond to user actions. |
| FlaskDemo/app.py and FlaskDemo/sample2.py | Flask application and routes | api.py: create_app, status, login, records, mutate | A URL reaches a Python function; JSON carries record values between desktop and server. |
| requestjson.py; ApiSearch.py | HTTP request and JSON response processing | faculty_desktop.ApiClient.request; holidays.get_json | Send a request, read the response, and show a useful error if the service is unavailable. The project uses standard-library urllib to keep one fewer dependency. |
| Regex-1.py, Regex-2.py, Regex-3.py | ID/email format checks and splitting tags | validation.identifier, email_address, tags | Regular expressions check whether text has an acceptable shape before saving. |
| studentcsv.py; studentcsv2.py | CSV data, filtering, averages, export | service.import_marks; reports.csv_report, analyse_marks | CSV holds rows; Pandas selects/groups those rows and calculates summaries. |
| streamlit/streamlit_demo/app.py | DataFrames, charts, student selection | ui.academic_progress, faculty_marks | Streamlit turns Python function calls into browser controls and charts. |
| streamlit/eighth_app.py | Marks averages, subject comparison, pass/fail summaries | reports.analyse_marks, assessment_ranking | This extends the same analysis to saved records and configurable subject thresholds. |
| Numpy exercises | Numerical mean and standard deviation | reports.analyse_marks | NumPy calculates numerical summaries after marks are converted to percentages. |
| tryexceptelsefinally.py; Divisionwithzero.py; networkException.py | Exceptions and cleanup | ui.perform; ApiClient.request; database.open_database | Invalid input is reported clearly; database connections close even when an operation fails. |
| file_handling1.py | Read/write text and binary files | CSV/XML reports, audit_text, backup.py | Reports use text/UTF-8; a SQLite backup is a binary file. The app does not unpickle untrusted files. |
| Classes and functions from notebooks | Named functions and ordinary classes | Planner, ApiClient, FacultyWindow, RecordForm | Related data/actions stay together; small helpers avoid repeating rules across interfaces. |

## Concepts added beyond the small exercises

- SQLite stores records persistently in linked tables rather than overwriting a CSV for every change.
- Password hashing and server-side permissions protect different student accounts.
- SQL placeholders separate entered values from query code.
- Transactions make an invalid CSV import roll back completely.
- XML ElementTree exports structured reports and escapes special characters.
- SQLite's backup API copies a consistent database rather than copying a potentially changing file.
- Automated tests use temporary databases to prove the flows without adding fictional records to the application.

These are explained in CODE_GUIDE.md. The project intentionally uses normal Python functions, loops, dictionaries, classes, and try/except blocks. The UI, API, and database are separate files so you can follow one action at a time.

## A short explanation you can adapt for class

Student Growth Planner combines academic tracking and college participation planning. Faculty create accounts, enrol students, and enter marks, assignments, clubs, and events. Students see their own progress, manage study tasks, compare clubs using explained rules, and record activities they completed. Streamlit provides the dashboard, PyQt provides faculty desktop forms, and Flask receives JSON requests from those forms. SQLite stores the records. Pandas and NumPy calculate summaries. The project starts empty and uses records entered by its users.

The project supports the idea behind SDG 4 Quality Education by helping students and faculty identify learning needs and plan development. It is a monitoring/planning tool; it does not prove educational outcomes or guarantee rewards.
