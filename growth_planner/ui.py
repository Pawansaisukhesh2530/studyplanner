"""Simple Streamlit screens. Service methods own validation and database writes."""

from datetime import date, datetime, time, timedelta
import sqlite3

import pandas as pd
import streamlit as st

from growth_planner.matching import recommend_clubs, split_tags
from growth_planner.backup import create_backup
from growth_planner.holidays import fetch_holidays
from growth_planner.reports import analyse_marks, assessment_ranking, csv_report, schedule, xml_report
from growth_planner.theme import auth_intro, club_heading, empty_state, overview_stats, section_note, status_badge, submit_button


def perform(function, *args, **kwargs):
    """Show a validation error, or refresh the screen after a successful save."""
    try:
        result = function(*args, **kwargs)
    except (ValueError, sqlite3.IntegrityError) as error:
        st.error(str(error))
        return
    st.session_state["notice"] = str(result)
    st.rerun()


def table(records):
    if records:
        st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
    else:
        empty_state()


def choose_record(label, records, identity, display, key):
    options = [None] + [row[identity] for row in records]
    names = {row[identity]: str(row[display]) + " (" + str(row[identity]) + ")" for row in records}
    chosen = st.selectbox(label, options, format_func=lambda item: "Add new" if item is None else names[item], key=key)
    return next((row for row in records if row[identity] == chosen), {})


def choose_id(label, records, identity, display, key=None):
    names = {row[identity]: str(row[display]) + " (" + str(row[identity]) + ")" for row in records}
    return st.selectbox(label, list(names), format_func=lambda item: names[item], key=key)


def login_screen(planner):
    setup = planner.setup_needed()
    with st.container(key="auth_layout"):
        introduction, account = st.columns([1.08, 1], gap="large")
        with introduction:
            auth_intro(setup)
        with account:
            with st.container(key="auth_card"):
                status_badge("LET’S GET YOU STARTED" if setup else "WELCOME BACK")
                st.header("Create the first faculty account" if setup else "Sign in")
                st.caption("Set up your college workspace. Your own records, from day one." if setup else "Your studies, plans, and campus life. Right where you left them.")
                with st.form("login"):
                    if setup:
                        first, second = st.columns(2)
                        username = first.text_input("Faculty ID", placeholder="Your faculty ID")
                        name = second.text_input("Full name", placeholder="Your full name")
                        email = st.text_input("Email", placeholder="name@college.edu")
                    else:
                        username = st.text_input("Account ID", placeholder="Enter your account ID")
                    password = st.text_input("Password (8–128 characters)", type="password", placeholder="Enter your password")
                    if setup:
                        confirmation = st.text_input("Confirm password", type="password", placeholder="Enter your password again")
                    submitted = submit_button("Create faculty account" if setup else "Sign in")
                st.markdown('<div class="gp-auth-footer">A dedicated workspace for faculty and students.</div>', unsafe_allow_html=True)
    if submitted:
        if setup:
            if password != confirmation:
                st.error("Passwords do not match.")
            else:
                perform(planner.setup_faculty, username, name, email, password)
        else:
            try:
                token = planner.login(username, password)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.clear()
                st.session_state["token"] = token
                st.rerun()


def password_screen(planner, token):
    st.subheader("Change password")
    with st.form("password"):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = submit_button("Change password")
    if submitted:
        if new != confirm:
            st.error("Passwords do not match.")
        else:
            perform(planner.change_password, token, old, new)


def faculty_home(planner, token):
    page = st.sidebar.radio("Faculty pages", ["Accounts and subjects", "Marks", "Assignments", "Clubs and events", "College calendar", "Student reports", "Backup and logs", "Account"])
    data = planner.snapshot(token)
    if page == "Accounts and subjects":
        section_note("FACULTY WORKSPACE", "A clear view of your college. Keep people, subjects, and learning connected.")
        overview_stats([
            ("Students", sum(user["role"] == "student" for user in data["users"])),
            ("Subjects", len(data["courses"])),
            ("Clubs & committees", len(data["clubs"])),
            ("Assignments", len(data["all_assignments"])),
        ])
        faculty_accounts(planner, token, data)
    elif page == "Marks":
        faculty_marks(planner, token, data)
    elif page == "Assignments":
        faculty_assignments(planner, token, data)
    elif page == "Clubs and events":
        faculty_clubs(planner, token, data)
    elif page == "College calendar":
        st.header("College holiday calendar")
        st.caption("Enter dates from your college's official calendar. Saving the same date updates its name.")
        table(data["college_holidays"])
        with st.form("college_holiday"):
            holiday_date = st.date_input("Holiday date")
            name = st.text_input("Holiday name")
            save = submit_button("Save college holiday")
        if save:
            perform(planner.save_college_holiday, token, holiday_date.isoformat(), name)
        if data["college_holidays"]:
            remove = choose_id("Holiday to remove", data["college_holidays"], "holiday_date", "name")
            confirm = st.checkbox("Remove this date from the college calendar")
            if st.button("Remove college holiday", disabled=not confirm):
                perform(planner.remove_college_holiday, token, remove)
    elif page == "Student reports":
        students = [user for user in data["users"] if user["role"] == "student"]
        if not students:
            st.info("Create a student account first.")
            return
        student = choose_id("Student", students, "username", "name")
        snapshot = planner.snapshot(token, student)
        academic_progress(snapshot)
        st.subheader("Completed participation")
        table(snapshot["activities"])
        download_reports(snapshot)
        st.download_button("Download audit log", planner.audit_text(token), "activity_log.txt", "text/plain")
    elif page == "Backup and logs":
        st.header("Backup and activity logs")
        if st.button("Prepare database backup"):
            st.session_state["backup_bytes"] = create_backup(planner, token)
        if "backup_bytes" in st.session_state:
            st.download_button("Download prepared backup", st.session_state["backup_bytes"], "student_growth_backup.db", "application/octet-stream")
            st.caption("This snapshot reflects the time you clicked Prepare. Prepare again after entering more records.")
        st.download_button("Download audit log", planner.audit_text(token), "activity_log.txt", "text/plain", key="backup_audit")
        st.write("To restore: stop all app components and run restore_backup.py. It checks your faculty password and the backup, asks you to type RESTORE, and saves a safety backup before replacing records.")
    else:
        table([planner.current_user(token)])
        password_screen(planner, token)


def faculty_accounts(planner, token, data):
    st.header("Accounts and subjects")
    st.caption("Start with accounts, add subjects, then connect each student through enrolments.")
    account_tab, course_tab, enrol_tab = st.tabs(["Accounts", "Subjects", "Enrolments"])
    with account_tab:
        table(data["users"])
        user = choose_record("Account to edit", data["users"], "username", "name", "edit_user")
        with st.form("account_" + user.get("username", "new")):
            identity, details = st.columns(2)
            username = identity.text_input("Account ID", user.get("username", ""), disabled=bool(user))
            name = details.text_input("Full name", user.get("name", ""))
            email_column, role_column = st.columns([2, 1])
            email = email_column.text_input("Email", user.get("email", ""))
            role = role_column.selectbox("Role", ["student", "faculty"], index=0 if user.get("role", "student") == "student" else 1, disabled=bool(user))
            password = st.text_input("Initial/reset password (leave empty to keep an existing password)", type="password")
            submitted = submit_button("Save account")
        if submitted:
            perform(planner.save_user, token, username, name, email, role, password)
    with course_tab:
        table(data["courses"])
        course = choose_record("Subject to edit", data["courses"], "code", "name", "edit_course")
        with st.form("course_" + course.get("code", "new")):
            code_column, name_column = st.columns([1, 2])
            code = code_column.text_input("Subject code", course.get("code", ""), disabled=bool(course))
            name = name_column.text_input("Subject name", course.get("name", ""))
            threshold = st.number_input("Pass percentage", 0.0, 100.0, float(course.get("pass_percentage", 40)))
            submitted = submit_button("Save subject")
        if submitted:
            perform(planner.save_course, token, code, name, threshold)
    with enrol_tab:
        table(data["enrolments"])
        students = [user for user in data["users"] if user["role"] == "student"]
        if students and data["courses"]:
            with st.form("enrol"):
                student = choose_id("Student", students, "username", "name")
                course = choose_id("Subject", data["courses"], "code", "name")
                submitted = submit_button("Enrol student")
            if submitted:
                perform(planner.enrol_student, token, student, course)
            st.caption("Removing an enrolment hides current assignments for that subject; previous marks and completion history remain stored.")
            with st.form("unenrol"):
                student = choose_id("Student", students, "username", "name", "unenrol_student")
                course = choose_id("Subject", data["courses"], "code", "name", "unenrol_course")
                confirm = st.checkbox("I intend to remove this enrolment")
                remove = submit_button("Remove enrolment")
            if remove:
                if confirm:
                    perform(planner.enrol_student, token, student, course, False)
                else:
                    st.error("Tick the confirmation before removing the enrolment.")
        else:
            st.info("Create a student and a subject before enrolling.")


def faculty_marks(planner, token, data):
    section_note("ACADEMIC RECORDS", "Keep every assessment accurate, and give students a clearer view of their progress.")
    st.header("Enter or correct marks")
    students = [user for user in data["users"] if user["role"] == "student"]
    if not students or not data["courses"]:
        st.info("Create students, subjects, and enrolments first.")
        return
    student = choose_id("Student", students, "username", "name", "marks_student")
    snapshot = planner.snapshot(token, student)
    table(snapshot["marks"])
    if snapshot["student_courses"]:
        selected = choose_record("Assessment to correct", snapshot["marks"], "id", "assessment", "edit_mark_" + student)
        with st.form("mark_" + student + "_" + str(selected.get("id", "new"))):
            codes = [row["code"] for row in snapshot["student_courses"]]
            code = st.selectbox("Subject code", codes, index=codes.index(selected["course_code"]) if selected else 0, disabled=bool(selected))
            title = st.text_input("Assessment name", selected.get("assessment", ""), disabled=bool(selected))
            when = st.date_input("Assessment date", date.fromisoformat(selected["assessment_date"]) if selected else date.today(), max_value=date.today(), disabled=bool(selected))
            maximum_column, score_column = st.columns(2)
            maximum = maximum_column.number_input("Maximum score", 0.01, 100000.0, float(selected.get("max_score", 100)))
            score = score_column.number_input("Score", 0.0, 100000.0, float(selected.get("score", 0)))
            submitted = submit_button("Save marks")
        if submitted:
            perform(planner.save_mark, token, student, code, title, when.isoformat(), score, maximum)
    else:
        st.info("Enrol the student in a subject before entering marks.")
    st.subheader("Import marks CSV")
    st.caption("The same student, subject code, assessment name, and date updates existing marks. Any invalid row cancels the whole import.")
    st.download_button("Download empty marks template", "student_id,course_code,assessment,assessment_date,score,max_score\n", "marks_template.csv", "text/csv")
    upload = st.file_uploader("Marks CSV", type="csv")
    if st.button("Import marks", disabled=upload is None):
        try:
            text = upload.getvalue().decode("utf-8-sig")
        except UnicodeDecodeError:
            st.error("Save the CSV as UTF-8.")
        else:
            perform(planner.import_marks, token, text)
    with st.expander("Class assessment comparison"):
        st.caption("Ranks compare only the same subject code, assessment name, date, and maximum score. Equal scores share a rank. Different assessments are not ranked together.")
        table(assessment_ranking(planner.class_marks(token)))


def faculty_assignments(planner, token, data):
    section_note("LEARNING IN MOTION", "Set clear work, share a deadline, and follow each student's reported completion.")
    st.header("Assignments")
    table(data["all_assignments"])
    if not data["courses"]:
        st.info("Create a subject first.")
        return
    assignment = choose_record("Assignment to edit", data["all_assignments"], "id", "title", "edit_assignment")
    with st.form("assignment_" + str(assignment.get("id", "new"))):
        codes = [row["code"] for row in data["courses"]]
        code = st.selectbox("Subject code", codes, index=codes.index(assignment["course_code"]) if assignment else 0, disabled=bool(assignment))
        title = st.text_input("Title", assignment.get("title", ""))
        instructions = st.text_area("Instructions", assignment.get("instructions", ""))
        due = st.date_input("Due date", date.fromisoformat(assignment["due_date"]) if assignment else date.today() + timedelta(days=7))
        submitted = submit_button("Save assignment")
    if submitted:
        perform(planner.save_assignment, token, code, title, instructions, due.isoformat(), assignment.get("id"))
    st.subheader("Student completion records")
    st.caption("Completion is reported by the student. It is not a grade or verified submission.")
    table(data["completions"])


def faculty_clubs(planner, token, data):
    section_note("LIFE BEYOND THE CLASSROOM", "Help students discover the experiences, people, and skills waiting around campus.")
    st.header("Clubs, committees, and events")
    club_tab, event_tab = st.tabs(["Club profiles", "Events"])
    with club_tab:
        table(data["clubs"])
        club = choose_record("Club to edit", data["clubs"], "club_id", "name", "edit_club")
        with st.form("club_" + club.get("club_id", "new")):
            code_column, name_column = st.columns([1, 2])
            club_id = code_column.text_input("Club ID", club.get("club_id", ""), disabled=bool(club))
            name = name_column.text_input("Club name", club.get("name", ""))
            category = st.text_input("Category", club.get("category", ""))
            description = st.text_area("Description and responsibilities", club.get("description", ""))
            interest_column, goal_column = st.columns(2)
            interests = interest_column.text_input("Interest tags (comma separated)", club.get("interests", ""))
            goals = goal_column.text_input("Goal tags (comma separated)", club.get("goals", ""))
            skills = st.text_input("Skills students may practise (comma separated)", club.get("skills", ""))
            hours = st.number_input("Expected hours per week", 0.5, 168.0, float(club.get("hours_per_week", 1)))
            examples = st.text_area("Typical activities", club.get("example_activities", ""))
            benefits = st.text_area("Possible benefits", club.get("potential_benefit", ""))
            submitted = submit_button("Save club")
        if submitted:
            perform(planner.save_club, token, club_id, name, category, description, interests, goals, skills, hours, examples, benefits)
    with event_tab:
        table(data["events"])
        if not data["clubs"]:
            st.info("Create a club first.")
            return
        event = choose_record("Event to edit", data["events"], "id", "title", "edit_event")
        with st.form("event_" + str(event.get("id", "new"))):
            ids = [row["club_id"] for row in data["clubs"]]
            club_id = st.selectbox("Club ID", ids, index=ids.index(event["club_id"]) if event else 0)
            title = st.text_input("Event title", event.get("title", ""))
            start, end = time_fields(event)
            location = st.text_input("Location", event.get("location", ""))
            submitted = submit_button("Save event")
        if submitted:
            perform(planner.save_event, token, club_id, title, start, end, location, event.get("id"))


def time_fields(record):
    start = datetime.fromisoformat(record["starts_at"]) if record else datetime.combine(date.today(), time(10))
    end = datetime.fromisoformat(record["ends_at"]) if record else start + timedelta(hours=1)
    start_date_column, start_time_column = st.columns(2)
    start_day = start_date_column.date_input("Start date", start.date())
    start_time = start_time_column.time_input("Start time", start.time())
    end_date_column, end_time_column = st.columns(2)
    end_day = end_date_column.date_input("End date", end.date())
    end_time = end_time_column.time_input("End time", end.time())
    st.caption("All times use the college's local time.")
    return datetime.combine(start_day, start_time).isoformat(timespec="minutes"), datetime.combine(end_day, end_time).isoformat(timespec="minutes")


def student_home(planner, token):
    page = st.sidebar.radio("Student pages", ["Academic progress", "Assignments and tasks", "Clubs", "Schedule", "Activity record", "Reports", "Account"])
    data = planner.snapshot(token)
    if page == "Academic progress":
        academic_progress(data)
    elif page == "Assignments and tasks":
        student_work(planner, token, data)
    elif page == "Clubs":
        student_clubs(planner, token, data)
    elif page == "Schedule":
        student_schedule(planner, token, data)
    elif page == "Activity record":
        student_activities(planner, token, data)
    elif page == "Reports":
        download_reports(data)
    else:
        table([data["profile"]])
        password_screen(planner, token)


def academic_progress(data):
    section_note("YOUR LEARNING JOURNEY", "See what is going well, find your next focus, and make each study session count.")
    st.header("Academic progress — " + data["profile"]["name"])
    result = analyse_marks(data["marks"])
    if result["overall"] is None:
        empty_state("Your progress starts here", "Once faculty enter your marks, your subject summaries and charts will appear here.")
    else:
        first, second, third = st.columns(3)
        first.metric("Average assessment percentage", str(result["overall"]) + "%")
        second.metric("Strongest subject", result["strongest"])
        third.metric("Subject to focus on", result["focus"])
        st.caption("Each assessment percentage has equal weight. Focus means the lowest recorded subject average. This is a planning summary, not an official final grade.")
        subjects, progress = st.columns(2, gap="large")
        with subjects:
            st.subheader("Your subjects at a glance")
            st.bar_chart(pd.DataFrame(result["subjects"]).set_index("subject")["average_percentage"], color="#51836a", y_label="Average %")
        with progress:
            st.subheader("Progress over time")
            st.line_chart(pd.DataFrame(result["trend"]).set_index("assessment_date")["percentage"], color="#387c70", y_label="Average %")
        st.caption("Score variation (standard deviation): " + str(result["variation"]) + " percentage points")
        table(result["subjects"])
        with st.expander("Assessment records"):
            table(result["assessments"])
    st.subheader("Enrolled subjects")
    table(data["student_courses"])


def student_work(planner, token, data):
    section_note("ONE STEP AT A TIME", "A little structure makes room for better learning. Keep your next steps close.")
    st.header("Assignments and study tasks")
    for assignment in data["assignments"]:
        with st.container(border=True, key="assignment_card_" + str(assignment["id"])):
            status_badge("COMPLETED" if assignment["completed_at"] else "TO DO", "green" if assignment["completed_at"] else "amber")
            st.subheader(assignment["title"])
            st.write(assignment["subject"] + " · due " + assignment["due_date"])
            st.write(assignment["instructions"])
            completed = bool(assignment["completed_at"])
            st.write("Completed: " + assignment["completed_at"] if completed else "Status: Open")
            if st.button("Mark open" if completed else "Mark complete", key="assignment_" + str(assignment["id"])):
                perform(planner.set_assignment_completion, token, assignment["id"], not completed)
    if not data["assignments"]:
        st.info("No assignments in your enrolled subjects yet.")
    st.subheader("Your study tasks")
    table(data["tasks"])
    task = choose_record("Study task to edit", data["tasks"], "id", "title", "edit_task")
    with st.form("task_" + str(task.get("id", "new"))):
        title_column, subject_column = st.columns(2)
        title = title_column.text_input("Task", task.get("title", ""))
        subject = subject_column.text_input("Subject", task.get("subject", ""))
        due_column, status_column = st.columns(2)
        due = due_column.date_input("Due date", date.fromisoformat(task["due_date"]) if task else date.today())
        status = status_column.selectbox("Status", ["Open", "Done"], index=1 if task.get("status") == "Done" else 0)
        submitted = submit_button("Save study task")
    if submitted:
        perform(planner.save_task, token, title, subject, due.isoformat(), task.get("id"), status)


def student_clubs(planner, token, data):
    section_note("FIND YOUR PLACE ON CAMPUS", "Follow your interests. Discover a club, learn something new, and make room for what matters to you.")
    st.header("Explore clubs and committees")
    profile = data["profile"]
    with st.form("preferences"):
        interest_column, goal_column = st.columns(2)
        interests = interest_column.text_input("Your interests (comma separated)", profile["interests"])
        goals = goal_column.text_input("Your goals (comma separated)", profile["goals"])
        hours = st.number_input("Available hours per week", 0.0, 168.0, float(profile["weekly_hours"]))
        submitted = submit_button("Save preferences")
    if submitted:
        perform(planner.save_preferences, token, interests, goals, hours)
    st.caption("Matching: 3 points per shared interest + 2 per shared goal + 2 when weekly time fits. Suggestions use your saved preferences.")
    status_by_club = {row["club_id"]: row["status"] for row in data["memberships"]}
    matches = recommend_clubs(data["clubs"], split_tags(profile["interests"]), split_tags(profile["goals"]), profile["weekly_hours"])
    if not matches:
        st.info("Faculty have not added clubs yet.")
    for match in matches:
        club = match["club"]
        with st.container(border=True, key="club_card_" + club["club_id"]):
            club_heading(club, match["score"])
            st.subheader(club["name"])
            st.write(club["description"])
            st.write("Typical activities: " + club["example_activities"])
            st.write("Skills you may practise: " + club["skills"].replace("|", ", "))
            st.write("Expected weekly hours: " + str(club["hours_per_week"]))
            st.write("Possible benefits: " + club["potential_benefit"])
            st.caption("; ".join(match["reasons"]))
            statuses = ["Remove", "Interested", "Participating"]
            with st.form("membership_" + club["club_id"]):
                status = st.selectbox("Your status", statuses, index=statuses.index(status_by_club.get(club["club_id"], "Remove")))
                submitted = submit_button("Save club status")
            if submitted:
                perform(planner.set_membership, token, club["club_id"], status)
    st.caption("Club status is self-reported. Possible benefits are not completed achievements or guaranteed rewards.")


def student_schedule(planner, token, data):
    section_note("MAKE TIME FOR WHAT MATTERS", "Bring your study plans and campus events together, with space to spot a busy day.")
    st.header("Schedule")
    result = schedule(data)
    st.subheader("College holidays entered by faculty")
    table(data["college_holidays"])
    for item in result["timed"]:
        names = [row["name"] for row in data["college_holidays"] if item["starts_at"][:10] <= row["holiday_date"] <= item["ends_at"][:10]]
        if names:
            st.warning(item["title"] + " is scheduled on a college holiday: " + ", ".join(names))
    st.caption("Events from clubs marked Interested or Participating appear with your study sessions. Touching end/start times do not count as clashes.")
    table(result["timed"])
    for clash in result["clashes"]:
        st.warning(clash["description"])
    st.subheader("Open deadlines")
    st.caption("Deadlines have dates only and are not treated as timed clashes.")
    table(result["deadlines"])
    st.subheader("Plan a study session")
    session = choose_record("Session to edit", data["study_sessions"], "id", "title", "edit_session")
    with st.form("session_" + str(session.get("id", "new"))):
        title = st.text_input("Session title", session.get("title", ""))
        start, end = time_fields(session)
        submitted = submit_button("Save study session")
    if submitted:
        perform(planner.save_study_session, token, title, start, end, session.get("id"))
    st.subheader("Public holiday lookup")
    st.caption("External public holidays are advisory. India may be unsupported; regional holidays and college closures may be missing. Verify against your college calendar. Lookup does not move or delete sessions.")
    with st.form("holiday_lookup"):
        country = st.text_input("Country code", "IN")
        year = st.number_input("Year", 2000, 2100, date.today().year)
        subdivision = st.text_input("Subdivision code (optional)")
        lookup = submit_button("Look up holidays")
    if lookup:
        st.session_state.pop("holiday_result", None)
        try:
            holidays = fetch_holidays(country, year, subdivision)
            st.session_state["holiday_result"] = {"country": country.upper(), "year": year, "holidays": holidays}
        except ValueError as error:
            st.warning(str(error))
    if "holiday_result" in st.session_state:
        saved = st.session_state["holiday_result"]
        st.write("Lookup: " + saved["country"] + " · " + str(saved["year"]))
        table(saved["holidays"])
        by_date = {row["date"]: row["name"] for row in saved["holidays"]}
        for item in result["timed"]:
            holiday_names = [name for day, name in by_date.items() if item["starts_at"][:10] <= day <= item["ends_at"][:10]]
            if holiday_names:
                st.info(item["title"] + " falls on a listed holiday: " + ", ".join(holiday_names))


def student_activities(planner, token, data):
    section_note("YOUR EXPERIENCES, RECORDED", "Big achievements begin with real participation. Keep a record of the work you have done.")
    st.header("Actual activity record")
    overview_stats([
        ("Completed activities", len(data["activities"])),
        ("Total recorded hours", sum(row["hours"] for row in data["activities"])),
        ("Clubs represented", len({row["club_id"] for row in data["activities"]})),
    ])
    table(data["activities"])
    if not data["clubs"]:
        st.info("Faculty need to create a club before you can record participation.")
        return
    activity = choose_record("Activity to correct", data["activities"], "id", "description", "edit_activity")
    ids = [row["club_id"] for row in data["clubs"]]
    club_id = st.selectbox("Club ID", ids, index=ids.index(activity["club_id"]) if activity else 0, key="activity_club_" + str(activity.get("id", "new")))
    events = [row for row in data["events"] if row["club_id"] == club_id]
    with st.form("activity_" + str(activity.get("id", "new")) + "_" + club_id):
        event_ids = [None] + [row["id"] for row in events]
        names = {row["id"]: row["title"] for row in events}
        previous_event = activity.get("event_id")
        event_id = st.selectbox("Related event (optional)", event_ids, index=event_ids.index(previous_event) if previous_event in event_ids else 0, format_func=lambda item: "No specific event" if item is None else names[item])
        when = st.date_input("Activity date", date.fromisoformat(activity["activity_date"]) if activity else date.today(), max_value=date.today())
        description = st.text_area("What you actually did", activity.get("description", ""))
        hours = st.number_input("Hours spent", 0.01, 24.0, float(activity.get("hours", 1)))
        skills = st.text_input("Skills practised (comma separated)", activity.get("skills_practised", ""))
        submitted = submit_button("Save completed activity")
    if submitted:
        perform(planner.save_activity, token, club_id, when.isoformat(), description, hours, skills, event_id, activity.get("id"))


def download_reports(data):
    st.header("Download reports")
    st.caption("Your progress, ready to take with you. Choose the format that fits your next step.")
    student = data["profile"]["username"]
    academic, activities, complete = st.columns(3)
    with academic:
        with st.container(border=True, key="report_card_marks"):
            status_badge("ACADEMICS")
            st.subheader("Your marks")
            st.caption("Assessment scores, ready to open in a spreadsheet.")
            st.download_button("Download marks CSV", csv_report(data["marks"], ["student_id", "course_code", "assessment", "assessment_date", "score", "max_score"]), student + "_marks.csv", "text/csv", width="stretch")
    with activities:
        with st.container(border=True, key="report_card_activities"):
            status_badge("CAMPUS LIFE")
            st.subheader("Your participation")
            st.caption("Completed activities, recorded hours, and practised skills.")
            st.download_button("Download activity CSV", csv_report(data["activities"], ["activity_date", "club", "description", "hours", "skills_practised"]), student + "_activities.csv", "text/csv", width="stretch")
    with complete:
        with st.container(border=True, key="report_card_complete"):
            status_badge("THE FULL PICTURE")
            st.subheader("Your growth record")
            st.caption("Your academic records and participation in one XML file.")
            st.download_button("Download complete XML report", xml_report(data), student + "_report.xml", "application/xml", width="stretch")

