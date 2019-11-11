from . import utils
from .transaction import ScheduleATransaction, ScheduleBTransaction


class Filing(utils.PyOpenFecApiPaginatedClass):
    def __init__(self, **kwargs):
        self.amendment_chain = None
        self.amendment_indicator = None
        self.amendment_version = None
        self.beginning_image_number = None
        self.candidate_id = None
        self.candidate_name = None
        self.cash_on_hand_beginning_period = None
        self.cash_on_hand_end_period = None
        self.cmte_tp = None
        self.committee_id = None
        self.committee_name = None
        self.coverage_end_date = None
        self.coverage_start_date = None
        self.csv_url = None
        self.cycle = None
        self.debts_owed_by_committee = None
        self.debts_owed_to_committee = None
        self.document_description = None
        self.document_type = None
        self.document_type_full = None
        self.election_year = None
        self.ending_image_number = None
        self.fec_file_id = None
        self.fec_url = None
        self.file_number = None
        self.form_type = None
        self.house_personal_funds = None
        self.html_url = None
        self.is_amended = None
        self.means_filed = None
        self.most_recent = None
        self.most_recent_file_number = None
        self.net_donations = None
        self.office = None
        self.opposition_personal_funds = None
        self.pages = None
        self.party = None
        self.pdf_url = None
        self.previous_file_number = None
        self.primary_general_indicator = None
        self.receipt_date = None
        self.report_type = None
        self.report_type_full = None
        self.report_year = None
        self.request_type = None
        self.senate_personal_funds = None
        self.state = None
        self.sub_id = None
        self.total_communication_cost = None
        self.total_disbursements = None
        self.total_independent_expenditures = None
        self.total_individual_contributions = None
        self.total_receipts = None
        self.treasurer_name = None
        self.update_date = None

        date_fields = {
            "coverage_end_date": "%Y-%m-%dT%H:%M:%S",
            "coverage_start_date": "%Y-%m-%dT%H:%M:%S",
            "receipt_date": "%Y-%m-%dT%H:%M:%S",
            "update_date": "%Y-%m-%dT%H:%M:%S",
        }

        for k, v in kwargs.items():
            utils.set_instance_attr(self, k, v, date_fields)

    def __str__(self):
        return "{cid}'s #{fn} Form {ft} ({rtf})".format(
            fn=self.file_number,
            cid=self.committee_id,
            ft=self.form_type,
            rtf=self.report_type_full,
        )

    @utils.default_empty_list
    def select_receipts(self, **kwargs):
        return [
            t
            for t in ScheduleATransaction.fetch(
                min_image_number=self.beginning_image_number,
                max_image_number=self.ending_image_number,
                **kwargs
            )
        ]

    @utils.default_empty_list
    def all_receipts(self):
        return [
            t
            for t in ScheduleATransaction.fetch(
                min_image_number=self.beginning_image_number,
                max_image_number=self.ending_image_number,
            )
        ]

    @utils.default_empty_list
    def select_disbursements(self, **kwargs):
        return [
            t
            for t in ScheduleBTransaction.fetch(
                min_image_number=self.beginning_image_number,
                max_image_number=self.ending_image_number,
                **kwargs
            )
        ]

    @utils.default_empty_list
    def all_disbursements(self):
        return [
            r
            for r in ScheduleBTransaction.fetch(
                min_image_number=self.beginning_image_number,
                max_image_number=self.ending_image_number,
            )
        ]
