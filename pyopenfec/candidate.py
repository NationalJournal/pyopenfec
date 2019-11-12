from collections import defaultdict
from datetime import datetime
from pytz import timezone

from . import utils
from .committee import Committee


class Candidate(utils.PyOpenFecApiPaginatedClass, utils.SearchMixin):

    def __init__(self, **kwargs):
        self.active_through = None
        self.address_city = None
        self.address_state = None
        self.address_street_1 = None
        self.address_street_2 = None
        self.address_zip = None
        self.candidate_id = None
        self.candidate_inactive = None
        self.candidate_status = None
        self.cycles = None
        self.district = None
        self.district_number = None
        self.election_districts = None
        self.election_years = None
        self.federal_funds_flag = None
        self.first_file_date = None
        self.flags = None
        self.has_raised_funds = None
        self.incumbent_challenge = None
        self.incumbent_challenge_full = None
        self.last_f2_date = None
        self.last_file_date = None
        self.load_date = None
        self.name = None
        self.office = None
        self.office_full = None
        self.party = None
        self.party_full = None
        self.state = None
        self._history = None
        self._committees = None

        eastern = timezone('US/Eastern')
        date_fields = {
            'first_file_date': '%Y-%m-%d',
            'last_f2_date': '%Y-%m-%d',
            'last_file_date': '%Y-%m-%d',
            'load_date': '%Y-%m-%dT%H:%M:%S',
            }

        for k, v in kwargs.items():
            if k in date_fields:
                parsed_date = datetime.strptime(v, date_fields[k])
                tz_aware = eastern.localize(parsed_date)
                setattr(self, k, tz_aware)
                continue
            setattr(self, k, v)

    def __unicode__(self):
        return unicode("{name} {id}".format(name=self.name,
                                            id=self.candidate_id))

    def __str__(self):
        return repr("{name} {id}".format(name=self.name,
                                         id=self.candidate_id))

    @property
    def history(self):
        if self._history is None:
            self._history = {}
            resource_path = 'candidate/{cid}/history'.format(cid=self.candidate_id)
            for hp in CandidateHistoryPeriod.fetch(resource=resource_path):
                self._history[hp.two_year_period] = hp
        return self._history

    @property
    def most_recent_cycle(self):
        return max(self.cycles)

    @property
    def committees(self):
        if self._committees is None:
            committees_by_cycle = defaultdict(list)
            for committee in Committee.fetch(candidate_id=self.candidate_id):
                for cycle in committee.cycles:
                    committees_by_cycle[cycle].append(committee)
            self._committees = dict(committees_by_cycle)
        return self._committees


class CandidateHistoryPeriod(utils.PyOpenFecApiPaginatedClass):

    def __init__(self, **kwargs):
        self.active_through = None
        self.address_city = None
        self.address_state = None
        self.address_street_1 = None
        self.address_street_2 = None
        self.address_zip = None
        self.candidate_election_year = None
        self.candidate_id = None
        self.candidate_inactive = None
        self.candidate_status = None
        self.cycles = None
        self.district = None
        self.district_number = None
        self.election_districts = None
        self.election_years = None
        self.first_file_date = None
        self.flags = None
        self.incumbent_challenge = None
        self.incumbent_challenge_full = None
        self.last_f2_date = None
        self.last_file_date = None
        self.load_date = None
        self.name = None
        self.office = None
        self.office_full = None
        self.party = None
        self.party_full = None
        self.state = None
        self.two_year_period = None

        eastern = timezone('US/Eastern')
        date_fields = {
            'first_file_date': '%Y-%m-%d',
            'last_f2_date': '%Y-%m-%d',
            'last_file_date': '%Y-%m-%d',
            'load_date': '%Y-%m-%dT%H:%M:%S',
            }

        for k, v in kwargs.items():
            if k in date_fields:
                parsed_date = datetime.strptime(v, date_fields[k])
                tz_aware = eastern.localize(parsed_date)
                setattr(self, k, tz_aware)
                continue
            setattr(self, k, v)

    def __unicode__(self):
        return unicode("{name} [{cand_id}] ({period})".format(
            name=self.name,
            cand_id=self.candidate_id,
            period=self.two_year_period))

    def __str__(self):
        return repr("{name} [{cand_id}] ({period})".format(
            name=self.name,
            cand_id=self.candidate_id,
            period=self.two_year_period))
