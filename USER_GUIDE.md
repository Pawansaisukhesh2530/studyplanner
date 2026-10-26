# How to use Student Growth Planner

## 1. Starting and understanding the windows

Double-click `Start-StudentGrowthPlanner.bat`. A command window starts Streamlit, and your browser opens the app at `http://127.0.0.1:8501`. Keep the command window open. You do not need the API or desktop app for browser use.

The app starts with no accounts, students, marks, clubs, or activities. Every displayed college record must be entered by you or deliberately imported. The old Version 1 dataset is not loaded.

For desktop faculty entry, start `Start-API.bat` first, then `Start-FacultyDesktop.bat`. Keep the API command window running while using desktop forms. Desktop saves appear in the browser when the browser next refreshes or you change pages.

## 2. Create your first faculty account

The first screen says **Create the first faculty account**. Enter your faculty ID, full name, email, password, and matching confirmation. Click **Create faculty account**.

The app validates the information, stores a salted password hash, saves the account, and switches to Sign in. There is no supplied/default password. IDs must contain 2–40 letters, digits, underscores, or hyphens and begin with a letter/digit. IDs are saved uppercase. Emails require a basic email format. Passwords must have 8–128 characters.

Enter your account ID and password and click **Sign in**. A successful login opens the faculty pages; an incorrect login displays an error without opening records. Login lasts up to eight hours. **Sign out** invalidates the session and returns to login.

New student/faculty accounts created later must change their initial password before using records. They enter the initial password as Current password, enter a different new password twice, and click **Change password**.

## 3. Faculty: Accounts and subjects

### Accounts tab

The table lists the actual accounts. **Account to edit → Add new** shows a blank form. Enter an ID, name, email, role, and initial password. Click **Save account**. The account appears in the table and can sign in immediately. Give credentials to the intended person yourself; the app does not email them.

To correct a profile, select it from Account to edit. The form fills with stored name/email. Change the details and click Save account. The account ID and role stay fixed so linked records retain their meaning.

For another person's forgotten password, select their account and enter a new initial/reset password. Saving invalidates their current sessions and makes them change that password next login. Leave this field empty to retain their existing password. Use the Account page to change your own password.

### Subjects tab

Select Add new, enter your actual subject code/name and the pass percentage used for your planning summaries, then click **Save subject**. To edit, select the subject first. The code stays fixed; the name and pass threshold can change. Changing the threshold recalculates the displayed pass/below-threshold summaries; it does not change entered marks.

### Enrolments tab

Choose a student and subject, then click **Enrol student**. This connects the account to that subject. The student can now see its assignments and faculty can record marks. Repeating the same enrolment does not create duplicates.

To undo a wrong enrolment, use the removal form, choose student/subject, tick the confirmation, and click **Remove enrolment**. Existing marks and saved completion history stay stored, but current subject assignments stop appearing for that student. Re-enrolling restores access to those assignments.

## 4. Faculty: Marks

Choose a student. Their existing marks appear. If they have no enrolled subjects, enrol them first.

To enter a result, choose Add new under Assessment to correct. Select a subject code, enter the assessment's actual name/date, maximum score, and achieved score. Click **Save marks**. The app checks enrolment, finite numeric values, date, and score bounds, then saves the result. Dates cannot be in the future. Scores must be zero or more and at most the maximum; maximum must be positive.

To correct a score, select the assessment in Assessment to correct. The identifying subject/name/date are fixed. Change Score or Maximum score and save. The existing result changes rather than adding a second copy. To avoid choosing the wrong result, check the table's student, subject, date, and record ID.

**Download empty marks template** downloads just the required CSV header. Fill it with your own records. Use existing IDs/codes and enrol students first. Select a UTF-8 CSV with **Marks CSV**, then click **Import marks**. You receive added/updated counts. Same student + subject code + assessment name + date means an update. Any invalid row rolls back the entire import; correct that row and retry.

Open **Class assessment comparison** to see ranks. Only results with the same subject code, assessment name, date, and maximum score are compared. Equal scores share a rank. A rank within a group of one does not imply a college-wide first rank.

## 5. Faculty: Assignments

Choose Add new, select a subject, enter title/instructions/deadline, and click **Save assignment**. Students enrolled in the subject can see it. Choose an existing assignment to edit the title, instructions, or deadline. Its subject stays fixed.

**Student completion records** shows each currently enrolled student's reported completion time or an empty value for open work. This is a completion tracker; the app does not collect answer files or automatically grade submissions.

## 6. Faculty: Clubs and events

### Club profiles

Choose Add new and fill the club's actual ID, name, category, description/responsibilities, interest tags, goal tags, skills, weekly hours, typical activities, and possible benefits. Tags can be separated with commas or `|`; matching ignores capitalization and removes duplicate tags. Click **Save club**.

The profile immediately becomes available to student matching. Enter clear, realistic responsibilities and time requirements. Possible benefits describe opportunities; record a certificate only as an offered benefit if your club actually offers it. Completed participation is recorded separately by students.

Select an existing club to correct its information and Save club again. Its ID stays fixed.

### Events

Create a club before creating an event. Choose Add new, select club, enter title, start/end dates and times, and location, then click **Save event**. End must be later than start. All times are the college's local time. Select an event to edit it. Moving an event to another club is rejected if existing activity records refer to the original club.

Events appear in a student's combined schedule when that student marks the club Interested or Participating.

## 7. Faculty: College calendar

Enter a holiday/closure date and its name from your official college calendar. Click **Save college holiday**. Saving the same date updates its name. Students see these dates on Schedule, with warnings for timed items occurring on those days.

To remove an incorrect entry, select it, tick **Remove this date from the college calendar**, then click **Remove college holiday**. Only that calendar date is removed; events and study sessions are not deleted.

## 8. Faculty: Student reports

Choose the student. The page shows their academic dashboard and completed participation. It uses the same calculations as the student dashboard. Download their marks CSV, activity CSV, or complete XML report. The audit log download is faculty-only and includes application action metadata for the college dataset.

## 9. Faculty: Backup and logs

Click **Prepare database backup** to create a consistent database snapshot. Then click **Download prepared backup** to save it to your chosen location. The snapshot contains the college records and password hashes; keep it private. Active login sessions are removed from the backup. Prepare again after adding more records if you want a newer copy.

**Download audit log** saves a tab-separated text file with UTC timestamp, account, action, and record key. It does not contain passwords or login tokens. Database-backed logging means normal saves and their audit records commit together.

To restore a saved database:

1. Close the desktop app and stop the browser/API servers with Ctrl+C.
2. Double-click `Restore-Backup.bat`.
3. Enter a current faculty ID and password. Password typing is hidden.
4. Enter the backup file's full path.
5. Type exactly `RESTORE` when prompted. Any other response cancels.
6. The utility validates the file's schema, integrity, references, and faculty account. It saves a safety copy of your current database under `data/backups/`, then restores the saved data.
7. Restart the app and sign in using the accounts/passwords that existed in the restored backup. All previous sessions are invalidated.

An invalid backup leaves records unchanged. Restore replaces the dataset rather than merging rows. Use a backup from this application version; the old Version 1 demo database is not compatible.

## 10. Student: Academic progress

Sign in with the account faculty created, and change the initial password when requested. Only your own academic records are available.

The page shows overall average assessment percentage, strongest subject, subject needing attention, variation, subject bar chart, date trend, subject summaries, and enrolled subjects. Expand **Assessment records** to inspect the original marks.

Each assessment is converted to `score / maximum × 100`. Overall average is the simple mean of these percentages; assessments have equal weight. Subject averages group assessments by subject. The focus subject has the lowest average among recorded subjects. With equal averages, the display uses a consistent alphabetical order; the label does not prove a meaningful difference between tied subjects. Standard deviation describes how spread out the assessment percentages are. Pass/below-threshold uses the faculty-entered subject threshold. These are planning summaries, not your official university result.

With no marks, you see a clear empty message rather than invented scores. Ask faculty to enter your results.

## 11. Student: Assignments and tasks

Assignment cards show subject, instructions, deadline, and status. **Mark complete** records the completion time and makes it visible to faculty. **Mark open** undoes your completion status. Completed assignments leave the open-deadline list; their original record remains.

For your own study tasks, choose Add new, enter task/subject/deadline, choose Open or Done, and click **Save study task**. To edit or complete a task, select it, change the details/status, and save. Faculty assignments and your personal tasks are separate records.

## 12. Student: Clubs

Enter interests and goals as comma-separated tags and your available hours per week. Click **Save preferences**. Rankings recalculate from your saved choices, so typing without saving does not change suggestions.

Each shared interest gives 3 points; each shared goal gives 2; a club requiring no more than your weekly availability gets 2 more. Reasons explain the score. Exact tag matching is used: `coding` matches `Coding`, but a different phrase is a different tag. A club that exceeds your time can still appear, with a warning in its reasons.

Read responsibilities, typical activities, skills, hours, and possible benefits. Set Your status to Interested or Participating, then click **Save club status**. This is your personal record, not official college admission. Remove clears that status and removes the club's events from your combined schedule. It does not erase completed participation.

## 13. Student: Schedule

The page shows college holidays, relevant club events, personal study sessions, overlapping-time warnings, and open assignment/task deadlines. Deadlines have dates only, so they are not treated as timed events. Sessions ending exactly when another begins do not clash.

Under Plan a study session, select Add new, enter title and start/end dates/times, and click **Save study session**. Select an existing session to edit it. Events are managed by faculty. Clash warnings advise you; they do not prevent saving or automatically move your plans.

For **Public holiday lookup**, enter country code, year, and optional subdivision code, then click **Look up holidays**. It calls the real external service. Returned national/regional scope is shown, and timed plans on listed dates are flagged. Results are labelled with the country/year queried. They are not saved as college holidays and do not move your schedule.

The service's supported-country list did not include India at verification. Unsupported countries and offline failures show a message. Use the real college calendar entered by faculty for Indian college closures. Without a subdivision, regional results may include areas outside your own location; check the scope. A public calendar is not a guarantee of a non-class day.

## 14. Student: Activity record

The table shows what you actually recorded and total hours. Choose Add new, choose a club, optionally choose one of that club's events, enter activity date, what you did, hours, and skills. Click **Save completed activity**.

Dates cannot be future dates. Hours must be above zero and no more than 24 per record. A linked event must have finished and the participation date must fall within its event dates. You may leave the event blank for genuine club work that had no scheduled event.

To correct an entry, select it under Activity to correct, change its details, and save. This record is self-reported participation; no certificate is automatically created or verified.

## 15. Student: Reports and Account

Reports provides **Download marks CSV**, **Download activity CSV**, and **Download complete XML report**. CSV can be opened in a spreadsheet; XML contains profile, courses, marks, assignments, tasks, memberships, participation, and study sessions. Reports contain your own records and no account password hashes. Empty reports still have valid headers/structure.

Account shows your profile/preferences and **Change password**. Enter current password and the new password twice. A successful change invalidates your other sessions while keeping the current one. Your faculty can correct your name/email.

## 16. Faculty desktop app

The desktop provides the same faculty account, subject, enrolment, marks, assignment, club, and event entry through Flask. Start the API first. Initial faculty setup is performed in the browser.

Enter faculty ID/password and click **Sign in**. Student logins are rejected here. If you must change the initial password, only Account opens until you do so.

Each record tab has an **Add new / existing record** selector. Selecting an existing record fills its fields. Click its **Save …** button to validate through the API and save. A Saved dialog appears, and all forms refresh. Account IDs/roles, subject codes, mark identifiers, and existing assignment subjects are fixed when editing. Numeric values are checked before submission and by the server. Use YYYY-MM-DD for dates and YYYY-MM-DDTHH:MM for local event times.

Desktop enrolment adds a connection; use the browser Enrolments tab to remove it. Desktop assignments/events pass the selected record ID when editing. Account contains **Change password**, **Refresh records**, and **Sign out**. Refresh reloads data entered elsewhere and clears unsaved form edits. Closing the desktop window signs out its session. Student reports, holiday lookup, CSV import, backups, and participation workflows use the browser.

## 17. Common problems

| What you see | What to do |
| --- | --- |
| Empty student/subject lists | Create accounts and subjects, then enrol students. |
| No marks/activities | Enter your real records; there is no demo seeding. |
| Incorrect ID or password | Check the faculty-created ID and password; ask faculty for a reset if needed. |
| Change initial password | Use the initial password as Current password and choose a different new password. |
| Session expired | Sign in again. |
| CSV row error | Correct the named row. Nothing from that import was saved. |
| Cannot reach API | Start Start-API.bat and keep its command window open. |
| Port already in use | Check whether that server is already running; use its existing window. |
| Holiday service unsupported/offline | Keep your saved schedule; consult the official college calendar. |
| Another computer cannot run copied .venv | Install Python and create a fresh environment using README.md. |

Your records persist when the browser/server is restarted. Keep `data/student_growth.db` and your saved backups. Do not delete the database to fix a login or display problem.
