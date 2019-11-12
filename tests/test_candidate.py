import unittest
from pyopenfec import Candidate
from datetime import datetime


class CandidateTest(unittest.TestCase):
    def setUp(self):
        self.candidate = None
        candidates = Candidate.fetch(candidate_id="H8CA05035")
        for candidate in candidates:
            self.candidate = candidate

    def test_candidate_dates(self):
        self.assertIsInstance(self.candidate.first_file_date, datetime)
        self.assertIsInstance(self.candidate.last_f2_date, datetime)
        self.assertIsInstance(self.candidate.last_file_date, datetime)
        self.assertIsInstance(self.candidate.load_date, datetime)

    def test_history_dates(self):
        history = self.candidate.history[2018]
        self.assertIsInstance(history.first_file_date, datetime)
        self.assertIsInstance(history.last_f2_date, datetime)
        self.assertIsInstance(history.last_file_date, datetime)
        self.assertIsInstance(history.load_date, datetime)
