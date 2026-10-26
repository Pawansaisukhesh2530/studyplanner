"""Core calculations and exports for the current application, without demo files."""

import csv
from io import StringIO
import unittest
from xml.etree import ElementTree as ET

from growth_planner.matching import recommend_clubs, split_tags
from growth_planner.reports import analyse_marks, csv_report, schedule, xml_report


class CoreTests(unittest.TestCase):
    def test_club_match_explains_ranking(self):
        clubs = [
            dict(name='Programming', interests='coding', goals='projects', hours_per_week=2),
            dict(name='Planning', interests='planning', goals='leadership', hours_per_week=5),
        ]
        matches = recommend_clubs(clubs, ['coding'], ['projects'], 3)
        self.assertEqual(matches[0]['club']['name'], 'Programming')
        self.assertEqual(matches[0]['score'], 7)
        self.assertIn('Shared interests: coding', matches[0]['reasons'])
        self.assertIn('Fits your weekly time', matches[0]['reasons'])
        self.assertIn('Needs more time than you selected', matches[1]['reasons'])

    def test_matching_tags_ignore_case_and_duplicates(self):
        self.assertEqual(split_tags(' Coding | technology |CODING|| '), {'coding', 'technology'})
        self.assertEqual(recommend_clubs([], [], [], 0), [])

    def test_academic_percentages_and_empty_state(self):
        records = [
            dict(id=1, course_code='PY', subject='Python', assessment_date='2026-10-24', score=42, max_score=50, pass_percentage=40),
            dict(id=2, course_code='DB', subject='Databases', assessment_date='2026-10-25', score=18, max_score=30, pass_percentage=70),
        ]
        result = analyse_marks(records)
        self.assertEqual(result['overall'], 72)
        self.assertEqual(result['variation'], 12)
        self.assertEqual(result['strongest'], 'Python')
        self.assertEqual(result['focus'], 'Databases')
        self.assertEqual(result['subjects'][1]['result'], 'Below threshold')
        self.assertEqual([row['percentage'] for row in result['trend']], [84, 60])
        self.assertIsNone(analyse_marks([])['overall'])

    def test_csv_and_xml_round_trip_and_escaping(self):
        output = csv_report([dict(title='=SUM(1,2)', hours=2)], ['title', 'hours'])
        record = next(csv.DictReader(StringIO(output)))
        self.assertEqual(record['title'], "'=SUM(1,2)")
        self.assertEqual(record['hours'], '2')
        snapshot = dict(profile=dict(username='REG01', name='A < B & C'), marks=[], activities=[dict(hours=2, description='Helped <team>')])
        root = ET.fromstring(xml_report(snapshot))
        self.assertEqual(root.find('profile/record/name').text, 'A < B & C')
        self.assertEqual(root.find('activity_summary/total_hours').text, '2')
        self.assertEqual(root.find('activity_summary/recorded_activities').text, '1')
        self.assertIsNotNone(root.find('academic_summary'))

    def test_date_only_deadlines_and_touching_sessions_do_not_clash(self):
        snapshot = dict(
            assignments=[dict(title='Assignment', due_date='2026-10-25', completed_at=None)],
            tasks=[dict(title='Revision', due_date='2026-10-25', status='Open')],
            study_sessions=[
                dict(id=1, title='First', starts_at='2026-10-25T10:00', ends_at='2026-10-25T11:00'),
                dict(id=2, title='Next', starts_at='2026-10-25T11:00', ends_at='2026-10-25T12:00'),
            ],
        )
        result = schedule(snapshot)
        self.assertEqual(result['clashes'], [])
        self.assertEqual(len(result['timed']), 2)
        self.assertEqual(len(result['deadlines']), 2)


if __name__ == '__main__':
    unittest.main()
