import unittest
from pyopenfec import Committee
from datetime import datetime


class CommitteeTest(unittest.TestCase):
    def setUp(self):
        self.committee = None
        committees = Committee.fetch(designation="P", candidate_id="H8CA05035")
        for committee in committees:
            self.committee = committee

    def test_committee_dates(self):
        self.assertIsInstance(self.committee.first_file_date, datetime)
        self.assertIsInstance(self.committee.last_f1_date, datetime)
        self.assertIsInstance(self.committee.last_file_date, datetime)

    def test_committee_history(self):
        history = self.committee.history[2016]
        self.assertEqual(history.cycle, 2016)

    def test_committee_totals_dates(self):
        totals = self.committee.totals[2018]
        self.assertIsInstance(totals.coverage_end_date, datetime)
        self.assertIsInstance(totals.coverage_start_date, datetime)

    def test_filing_dates(self):
        example_filing = None
        for filing in self.committee.select_filings(file_number=1186352):
            example_filing = filing
        self.assertIsInstance(example_filing.coverage_end_date, datetime)
        self.assertIsInstance(example_filing.coverage_start_date, datetime)
        self.assertIsInstance(example_filing.receipt_date, datetime)
        self.assertIsInstance(example_filing.update_date, datetime)

    def test_receipts_by_state(self):
        schedule_a = self.committee.total_receipts_by_state(cycle=2008)[0]
        self.assertEqual(schedule_a.cycle, 2008)
        self.assertEqual(schedule_a.committee_id, self.committee.committee_id)

    def test_receipts_by_size(self):
        schedule_a = self.committee.total_receipts_by_size(cycle=2008)[0]
        self.assertEqual(schedule_a.cycle, 2008)
        self.assertEqual(schedule_a.committee_id, self.committee.committee_id)

    def test_receipts_by_zip(self):
        schedule_a = self.committee.total_receipts_by_zip(cycle=2008)[0]
        self.assertEqual(schedule_a.cycle, 2008)
        self.assertEqual(schedule_a.committee_id, self.committee.committee_id)

    def test_report_dates(self):
        example_report = None
        for report in self.committee.select_reports(file_number=1234452):
            example_report = report
        self.assertIsInstance(example_report.coverage_end_date, datetime)
        self.assertIsInstance(example_report.coverage_start_date, datetime)
        self.assertIsInstance(example_report.receipt_date, datetime)

    def test_schedule_a_dates(self):
        example = None
        donations = self.committee.select_receipts(
            contributor_name="SANDBERG, SHERYL", two_year_transaction_period=2018
        )
        for donation in donations:
            example = donation
        self.assertIsInstance(example.contribution_receipt_date, datetime)
        self.assertIsInstance(example.load_date, datetime)

    def test_schedule_b_dates(self):
        example = None
        donations = self.committee.select_disbursements(
            recipient_name="GOAT HILL PIZZA", two_year_transaction_period=2018
        )
        for donation in donations:
            example = donation
        self.assertIsInstance(example.disbursement_date, datetime)
        self.assertIsInstance(example.load_date, datetime)
