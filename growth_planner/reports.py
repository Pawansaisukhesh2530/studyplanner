"""Readable reports and schedule calculations, without changing saved records."""

import csv
from io import StringIO
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd


def analyse_marks(records):
    if not records:
        return {"overall": None, "subjects": [], "trend": [], "variation": None,
                "strongest": None, "focus": None, "assessments": []}
    frame = pd.DataFrame(records)
    frame["percentage"] = frame["score"] / frame["max_score"] * 100
    frame["result"] = np.where(frame["percentage"] >= frame["pass_percentage"], "Pass", "Below threshold")
    summary = frame.groupby(["course_code", "subject"], as_index=False).agg(
        average_percentage=("percentage", "mean"), assessments=("id", "count"),
        pass_percentage=("pass_percentage", "first"))
    summary["result"] = np.where(summary["average_percentage"] >= summary["pass_percentage"], "Pass", "Below threshold")
    summary["average_percentage"] = summary["average_percentage"].round(1)
    summary = summary.sort_values(["average_percentage", "subject"], ascending=[False, True])
    trend = frame.groupby("assessment_date", as_index=False)["percentage"].mean().round(1)
    return {"overall": round(float(np.mean(frame["percentage"])), 1),
            "variation": round(float(np.std(frame["percentage"])), 1),
            "subjects": summary.to_dict("records"), "trend": trend.to_dict("records"),
            "strongest": summary.iloc[0]["subject"], "focus": summary.iloc[-1]["subject"],
            "assessments": frame.round({"percentage": 1}).to_dict("records")}


def assessment_ranking(records):
    """Rank only the same course, named assessment, date, and maximum score."""
    if not records:
        return []
    frame = pd.DataFrame(records)
    keys = ["course_code", "assessment", "assessment_date", "max_score"]
    frame["rank"] = frame.groupby(keys)["score"].rank(method="min", ascending=False).astype(int)
    frame["group_size"] = frame.groupby(keys)["score"].transform("count")
    frame["percentage"] = (frame["score"] / frame["max_score"] * 100).round(1)
    if "pass_percentage" in frame:
        frame["result"] = np.where(frame["score"] / frame["max_score"] * 100 >= frame["pass_percentage"], "Pass", "Below threshold")
    return frame.to_dict("records")


def schedule(snapshot):
    selected = {row["club_id"] for row in snapshot.get("memberships", [])}
    timed = []
    for row in snapshot.get("events", []):
        if row["club_id"] in selected:
            timed.append({"key": "event-" + str(row["id"]), "kind": "Club event", "title": row["title"],
                          "starts_at": row["starts_at"], "ends_at": row["ends_at"], "location": row["location"]})
    for row in snapshot.get("study_sessions", []):
        timed.append({"key": "study-" + str(row["id"]), "kind": "Study", "title": row["title"],
                      "starts_at": row["starts_at"], "ends_at": row["ends_at"], "location": ""})
    timed.sort(key=lambda item: item["starts_at"])
    clashes = []
    for index, first in enumerate(timed):
        for second in timed[index + 1:]:
            if second["starts_at"] >= first["ends_at"]:
                break
            if first["starts_at"] < second["ends_at"]:
                clashes.append({"first": first["key"], "second": second["key"],
                                "description": first["title"] + " overlaps " + second["title"]})
    deadlines = []
    for row in snapshot.get("assignments", []):
        if not row["completed_at"]:
            deadlines.append({"date": row["due_date"], "kind": "Assignment", "title": row["title"]})
    for row in snapshot.get("tasks", []):
        if row["status"] == "Open":
            deadlines.append({"date": row["due_date"], "kind": "Study task", "title": row["title"]})
    return {"timed": timed, "clashes": clashes, "deadlines": sorted(deadlines, key=lambda row: row["date"])}


def csv_report(records, columns):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        # Spreadsheet programs should display user-entered text, not run it as a formula.
        safe = {key: ("'" + value if isinstance(value, str) and value[:1] in ("=", "+", "-", "@") else value)
                for key, value in record.items()}
        writer.writerow(safe)
    return output.getvalue()


def xml_report(snapshot):
    root = ET.Element("student_growth_report")
    for section in ("profile", "student_courses", "marks", "assignments", "tasks", "memberships", "activities", "study_sessions"):
        container = ET.SubElement(root, section)
        records = [snapshot[section]] if section == "profile" else snapshot.get(section, [])
        for record in records:
            item = ET.SubElement(container, "record")
            for key, value in record.items():
                ET.SubElement(item, key).text = "" if value is None else str(value)
    analysis = analyse_marks(snapshot.get("marks", []))
    summary = ET.SubElement(root, "academic_summary")
    for key in ("overall", "variation", "strongest", "focus"):
        ET.SubElement(summary, key).text = "" if analysis[key] is None else str(analysis[key])
    for subject in analysis["subjects"]:
        item = ET.SubElement(summary, "subject")
        for key, value in subject.items():
            ET.SubElement(item, key).text = str(value)
    participation = ET.SubElement(root, "activity_summary")
    ET.SubElement(participation, "recorded_activities").text = str(len(snapshot.get("activities", [])))
    ET.SubElement(participation, "total_hours").text = str(sum(row["hours"] for row in snapshot.get("activities", [])))
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
