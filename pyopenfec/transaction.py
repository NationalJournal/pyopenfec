from . import utils


class ScheduleATransaction(utils.PyOpenFecApiIndexedClass):
    def __init__(self, **kwargs):
        self.amendment_indicator = None
        self.amendment_indicator_desc = None
        self.back_reference_schedule_name = None
        self.back_reference_transaction_id = None
        self.candidate_first_name = None
        self.candidate_id = None
        self.candidate_last_name = None
        self.candidate_middle_name = None
        self.candidate_name = None
        self.candidate_office = None
        self.candidate_office_district = None
        self.candidate_office_full = None
        self.candidate_office_state = None
        self.candidate_office_state_full = None
        self.candidate_prefix = None
        self.candidate_suffix = None
        self.committee = None
        self.committee_id = None
        self.committee_name = None
        self.conduit_committee_city = None
        self.conduit_committee_id = None
        self.conduit_committee_name = None
        self.conduit_committee_state = None
        self.conduit_committee_street1 = None
        self.conduit_committee_street2 = None
        self.conduit_committee_zip = None
        self.contribution_receipt_amount = None
        self.contribution_receipt_date = None
        self.contributor = None
        self.contributor_aggregate_ytd = None
        self.contributor_city = None
        self.contributor_employer = None
        self.contributor_first_name = None
        self.contributor_id = None
        self.contributor_last_name = None
        self.contributor_middle_name = None
        self.contributor_name = None
        self.contributor_occupation = None
        self.contributor_prefix = None
        self.contributor_state = None
        self.contributor_street_1 = None
        self.contributor_street_2 = None
        self.contributor_suffix = None
        self.contributor_zip = None
        self.cycle = None
        self.donor_committee_name = None
        self.election_type = None
        self.election_type_full = None
        self.entity_type = None
        self.entity_type_desc = None
        self.fec_election_type_desc = None
        self.fec_election_year = None
        self.file_number = None
        self.filing_form = None
        self.image_number = None
        self.increased_limit = None
        self.is_individual = None
        self.line_number = None
        self.line_number_label = None
        self.link_id = None
        self.load_date = None
        self.memo_code = None
        self.memo_code_full = None
        self.memo_text = None
        self.memoed_subtotal = None
        self.national_committee_nonfederal_account = None
        self.original_sub_id = None
        self.pdf_url = None
        self.receipt_type = None
        self.receipt_type_desc = None
        self.receipt_type_full = None
        self.report_type = None
        self.report_year = None
        self.schedule_type = None
        self.schedule_type_full = None
        self.sub_id = None
        self.timestamp = None
        self.transaction_id = None
        self.two_year_transaction_period = None
        self.unused_contbr_id = None

        date_fields = {
            "contribution_receipt_date": "%Y-%m-%dT%H:%M:%S",
            "load_date": "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "timestamp": "%Y-%m-%dT%H:%M:%S.%f+00:00",
        }

        for k, v in kwargs.items():
            utils.set_instance_attr(self, k, v, date_fields)

    @classmethod
    def fetch(cls, **kwargs):
        if "resource" not in kwargs:
            kwargs["resource"] = "schedules/schedule_a"

        for record in super(ScheduleATransaction, cls).fetch(**kwargs):
            yield record

    def __str__(self):
        return repr(
            "{cid} receipt: {fn} ({t}, {d})".format(
                cid=self.committee_id,
                fn=self.file_number,
                t=self.tran_id,
                d=self.receipt_date,
            )
        )


class ScheduleBTransaction(utils.PyOpenFecApiIndexedClass):
    def __init__(self, **kwargs):
        self.amendment_indicator = None
        self.amendment_indicator_desc = None
        self.back_reference_schedule_name = None
        self.back_reference_transaction_id = None
        self.candidate_first_name = None
        self.candidate_id = None
        self.candidate_last_name = None
        self.candidate_middle_name = None
        self.candidate_name = None
        self.candidate_office = None
        self.candidate_office_district = None
        self.candidate_office_full = None
        self.candidate_office_state = None
        self.candidate_office_state_full = None
        self.candidate_prefix = None
        self.candidate_suffix = None
        self.committee = None
        self.committee_id = None
        self.committee_name = None
        self.conduit_committee_city = None
        self.conduit_committee_id = None
        self.conduit_committee_name = None
        self.conduit_committee_state = None
        self.conduit_committee_street1 = None
        self.conduit_committee_street2 = None
        self.conduit_committee_zip = None
        self.contribution_receipt_amount = None
        self.contribution_receipt_date = None
        self.contributor = None
        self.contributor_aggregate_ytd = None
        self.contributor_city = None
        self.contributor_employer = None
        self.contributor_first_name = None
        self.contributor_id = None
        self.contributor_last_name = None
        self.contributor_middle_name = None
        self.contributor_name = None
        self.contributor_occupation = None
        self.contributor_prefix = None
        self.contributor_state = None
        self.contributor_street_1 = None
        self.contributor_street_2 = None
        self.contributor_suffix = None
        self.contributor_zip = None
        self.cycle = None
        self.donor_committee_name = None
        self.election_type = None
        self.election_type_full = None
        self.entity_type = None
        self.entity_type_desc = None
        self.fec_election_type_desc = None
        self.fec_election_year = None
        self.file_number = None
        self.filing_form = None
        self.image_number = None
        self.increased_limit = None
        self.is_individual = None
        self.line_number = None
        self.line_number_label = None
        self.link_id = None
        self.load_date = None
        self.memo_code = None
        self.memo_code_full = None
        self.memo_text = None
        self.memoed_subtotal = None
        self.national_committee_nonfederal_account = None
        self.original_sub_id = None
        self.pdf_url = None
        self.receipt_type = None
        self.receipt_type_desc = None
        self.receipt_type_full = None
        self.report_type = None
        self.report_year = None
        self.schedule_type = None
        self.schedule_type_full = None
        self.sub_id = None
        self.timestamp = None
        self.transaction_id = None
        self.two_year_transaction_period = None
        self.unused_contbr_id = None

        date_fields = {
            "disbursement_date": "%Y-%m-%dT%H:%M:%S",
            "load_date": "%Y-%m-%dT%H:%M:%S.%f+00:00",
        }

        for k, v in kwargs.items():
            utils.set_instance_attr(self, k, v, date_fields)

    @classmethod
    def fetch(cls, **kwargs):
        if "resource" not in kwargs:
            kwargs["resource"] = "schedules/schedule_b"

        for record in super(ScheduleBTransaction, cls).fetch(**kwargs):
            yield record

    def __str__(self):
        return repr(
            "{cid} receipt: {fn} ({t}, {d})".format(
                cid=self.committee_id,
                fn=self.file_number,
                t=self.tran_id,
                d=self.disbursement_date,
            )
        )
