from . import utils


class EfileReport(utils.PyOpenFecApiPaginatedClass):
    """A raw e-filed House/Senate report (Form 3) from ``/efile/reports/house-senate/``.

    E-filings appear within minutes of being filed, well before the processed
    reports behind ``Committee.select_reports`` exist, which makes this the
    resource for filing-night work.

    Every field OpenFEC documents for the endpoint (plus the summary money
    fields it returns alongside them) is an attribute defaulting to ``None``,
    so a field missing from a result reads as ``None`` rather than raising.
    Fields the API adds later are still set as attributes.

    ``coverage_start_date``, ``coverage_end_date`` and ``receipt_date`` are
    coerced to timezone-aware ``US/Eastern`` datetimes, exactly as ``Report``
    does, so the two resources can be handled by the same code. Other date
    strings (``election_date``, ``sign_date``) are left as the API returns them.
    """

    resource_path = "efile/reports/house-senate"

    def __init__(self, **kwargs):
        self.amended_address = None
        self.amended_by = None
        self.amendment = None
        self.amendment_chain = None
        self.beginning_image_number = None
        self.candidate_contribution_period = None
        self.candidate_first_name = None
        self.candidate_id = None
        self.candidate_last_name = None
        self.candidate_middle_name = None
        self.candidate_name = None
        self.candidate_prefix = None
        self.candidate_suffix = None
        self.cash_on_hand_beginning_period = None
        self.cash_on_hand_end_period = None
        self.city = None
        self.committee_id = None
        self.committee_name = None
        self.coverage_end_date = None
        self.coverage_start_date = None
        self.csv_url = None
        self.district = None
        self.document_description = None
        self.election_date = None
        self.election_state = None
        self.f3z1 = None
        self.fec_file_id = None
        self.fec_url = None
        self.file_number = None
        self.general_election = None
        self.is_amended = None
        self.loans_made_by_candidate_period = None
        self.most_recent = None
        self.most_recent_filing = None
        self.pdf_url = None
        self.prefix = None
        self.primary_election = None
        self.receipt_date = None
        self.report = None
        self.report_type = None
        self.report_year = None
        self.rpt_pgi = None
        self.runoff_election = None
        self.sign_date = None
        self.special_election = None
        self.state = None
        self.street_1 = None
        self.street_2 = None
        self.suffix = None
        self.summary_lines = None
        self.total_contribution_refunds_period = None
        self.total_disbursements_period = None
        self.total_disbursements_ytd = None
        self.total_receipts_period = None
        self.total_receipts_ytd = None
        self.treasurer_first_name = None
        self.treasurer_last_name = None
        self.treasurer_middle_name = None
        self.treasurer_name = None
        self.zip = None

        date_fields = {
            "coverage_end_date": "%Y-%m-%d",
            "coverage_start_date": "%Y-%m-%d",
            "receipt_date": "%Y-%m-%dT%H:%M:%S",
        }

        for k, v in kwargs.items():
            utils.set_instance_attr(self, k, v, date_fields)

    def __str__(self):
        return repr(
            "{cid} {rt} #{fn} ({csd}-{ced})".format(
                cid=self.committee_id,
                rt=self.report_type,
                fn=self.file_number,
                csd=self.coverage_start_date,
                ced=self.coverage_end_date,
            )
        )

    @classmethod
    def fetch(cls, **kwargs):
        # The endpoint is not named after the class, so default the resource
        # path instead of asking every caller to pass resource=.
        kwargs.setdefault("resource", cls.resource_path)
        return super(EfileReport, cls).fetch(**kwargs)
