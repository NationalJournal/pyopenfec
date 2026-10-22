"""EfileReport resource and Committee.select_efile_reports, offline.

Acceptance criteria (spec: pyopenfec-efile-report-handoff.md, Scope):
  AC-A  EfileReport on the paginated base, resource efile/reports/house-senate,
        response fields exposed as attributes; missing fields are None.
  AC-B  Committee.select_efile_reports(**kwargs) passes committee_id plus kwargs
        and paginates.
"""
import unittest
from datetime import datetime
from unittest import mock

from pyopenfec import Committee, EfileReport
from pyopenfec import utils

from .support import FakeTransport, TEST_API_KEY, json_response, page, patch_env

MONEY_FIELDS = [
    "total_disbursements_period",
    "total_receipts_period",
    "loans_made_by_candidate_period",
    "candidate_contribution_period",
    "cash_on_hand_end_period",
    "total_receipts_ytd",
    "total_disbursements_ytd",
    "total_contribution_refunds_period",
]


def efile_row(file_number=1234567, report_type="Q3", **overrides):
    row = {
        "committee_id": "C00000001",
        "committee_name": "FRIENDS OF SOMEBODY",
        "file_number": file_number,
        "report_type": report_type,
        "coverage_start_date": "2026-07-01",
        "coverage_end_date": "2026-09-30",
        "receipt_date": "2026-10-15T16:20:00",
        "candidate_id": "H0OH08001",
        "is_amended": False,
        "pdf_url": "https://docquery.fec.gov/pdf/123/{}/{}.pdf".format(file_number, file_number),
    }
    for index, field in enumerate(MONEY_FIELDS):
        row[field] = 1000.0 + index
    row.update(overrides)
    return row


class EfileTestCase(unittest.TestCase):
    def setUp(self):
        patch_env(self)
        sleep = mock.patch.object(utils.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        utils._last_request_at = None


class EfileReportResourceTestCase(EfileTestCase):
    """AC-A"""

    def test_fetch_uses_house_senate_resource_with_key_and_params(self):
        with FakeTransport(json_response(200, page([efile_row()]))) as transport:
            reports = list(EfileReport.fetch(committee_id="C00000001"))
        self.assertEqual(len(reports), 1)
        self.assertIsInstance(reports[0], EfileReport)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(transport.path(), "/v1/efile/reports/house-senate/")
        self.assertEqual(transport.query()["api_key"], TEST_API_KEY)
        self.assertEqual(transport.query()["committee_id"], "C00000001")

    def test_response_fields_are_attributes(self):
        with FakeTransport(json_response(200, page([efile_row()]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        self.assertEqual(report.committee_id, "C00000001")
        self.assertEqual(report.file_number, 1234567)
        self.assertEqual(report.report_type, "Q3")
        for index, field in enumerate(MONEY_FIELDS):
            self.assertEqual(getattr(report, field), 1000.0 + index, field)
        self.assertEqual(report.pdf_url, "https://docquery.fec.gov/pdf/123/1234567/1234567.pdf")

    def test_dates_are_coerced_to_eastern_datetimes_like_report(self):
        with FakeTransport(json_response(200, page([efile_row()]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        for field, expected in (
            ("coverage_start_date", datetime(2026, 7, 1)),
            ("coverage_end_date", datetime(2026, 9, 30)),
            ("receipt_date", datetime(2026, 10, 15, 16, 20)),
        ):
            value = getattr(report, field)
            self.assertIsInstance(value, datetime, field)
            self.assertEqual(value.tzinfo.zone, "US/Eastern", field)
            self.assertEqual(value.replace(tzinfo=None), expected, field)

    def test_missing_fields_are_none_not_attribute_errors(self):
        row = efile_row()
        del row["cash_on_hand_end_period"]
        del row["loans_made_by_candidate_period"]
        del row["coverage_end_date"]
        with FakeTransport(json_response(200, page([row]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        self.assertIsNone(report.cash_on_hand_end_period)
        self.assertIsNone(report.loans_made_by_candidate_period)
        self.assertIsNone(report.coverage_end_date)
        self.assertEqual(report.total_receipts_period, 1001.0)

    def test_null_date_stays_none(self):
        with FakeTransport(json_response(200, page([efile_row(receipt_date=None)]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        self.assertIsNone(report.receipt_date)

    def test_unknown_fields_are_still_set(self):
        with FakeTransport(json_response(200, page([efile_row(brand_new_field="x")]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        self.assertEqual(report.brand_new_field, "x")

    def test_empty_results(self):
        with FakeTransport(json_response(200, page([], pages=0))) as transport:
            reports = list(EfileReport.fetch(committee_id="C00000001"))
        self.assertEqual(reports, [])
        self.assertEqual(len(transport.requests), 1)

    def test_str_names_committee_report_and_coverage(self):
        with FakeTransport(json_response(200, page([efile_row()]))):
            report = list(EfileReport.fetch(committee_id="C00000001"))[0]
        self.assertIn("C00000001", str(report))
        self.assertIn("Q3", str(report))


class CommitteeSelectEfileReportsTestCase(EfileTestCase):
    """AC-B"""

    def setUp(self):
        super(CommitteeSelectEfileReportsTestCase, self).setUp()
        self.committee = Committee(committee_id="C00000001", name="FRIENDS OF SOMEBODY")

    def test_passes_committee_id_and_kwargs(self):
        with FakeTransport(json_response(200, page([efile_row()]))) as transport:
            reports = self.committee.select_efile_reports(
                min_receipt_date="2026-06-30", max_receipt_date="2026-10-16", sort="-receipt_date"
            )
        self.assertEqual(len(reports), 1)
        self.assertIsInstance(reports[0], EfileReport)
        query = transport.query()
        self.assertEqual(transport.path(), "/v1/efile/reports/house-senate/")
        self.assertEqual(query["committee_id"], "C00000001")
        self.assertEqual(query["min_receipt_date"], "2026-06-30")
        self.assertEqual(query["max_receipt_date"], "2026-10-16")
        self.assertEqual(query["sort"], "-receipt_date")
        self.assertEqual(query["api_key"], TEST_API_KEY)

    def test_returns_empty_list_when_no_results(self):
        with FakeTransport(json_response(200, page([], pages=0))):
            self.assertEqual(self.committee.select_efile_reports(), [])

    def test_paginates_over_every_page(self):
        first = page([efile_row(1), efile_row(2)], pages=3, count=5, per_page=2, current=1)
        second = page([efile_row(3), efile_row(4)], pages=3, count=5, per_page=2, current=2)
        third = page([efile_row(5)], pages=3, count=5, per_page=2, current=3)
        with FakeTransport(
            json_response(200, first), json_response(200, second), json_response(200, third)
        ) as transport:
            reports = self.committee.select_efile_reports(sort="-receipt_date")
        self.assertEqual([r.file_number for r in reports], [1, 2, 3, 4, 5])
        self.assertEqual(len(transport.requests), 3)
        self.assertNotIn("page", transport.query(0))
        self.assertEqual(transport.query(1)["page"], "2")
        self.assertEqual(transport.query(2)["page"], "3")
        for index in range(3):
            self.assertEqual(transport.query(index)["committee_id"], "C00000001")
            self.assertEqual(transport.query(index)["sort"], "-receipt_date")

    def test_exported_from_package_root(self):
        import pyopenfec

        self.assertIs(pyopenfec.EfileReport, EfileReport)
