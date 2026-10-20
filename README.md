# PyOpenFec
A Python wrapper for the OpenFEC API. Documentation for this API can be found [here](https://api.open.fec.gov/developers)

## Installation
```
pip install pyopenfec
```

## Examples

### Candidates

#### Candidate
The `Candidate` class holds fields for each candidate in the OpenFEC API.

A number of class and instance methods are available.

##### count
The `Candidate.count()` method will return the number of Candidate objects available for a given query. Note: This method returns an integer representing the number of items available in the OpenFEC API. It does not return a list of objects.
```
from pyopenfec import Candidate
candidate_count = Candidate.count(cycle=2016, office="P", candidate_status="C")
```

#### fetch
The `Candidate.fetch()` method will return a list of Candidate objects available for a given query. This method will automatically page through the results and return all objects available in the OpenFEC API.
```
from pyopenfec import Candidate
candidate_count = Candidate.count(cycle=2016, office="P", candidate_status="C")
candidates = Candidate.fetch(cycle=2016, office="P", candidate_status="C")
for candidate in candidates:
    print("{name}, {party}".format(name=candidate.name, party=candidate.party))
```
### Committees
tktk

### Reports
tktk

### E-filed reports
`EfileReport` wraps `/efile/reports/house-senate/`, the raw e-filings that appear within minutes of being filed. `Committee.select_efile_reports()` pages through every result for a committee and accepts the endpoint's query parameters.
```
from pyopenfec import Committee
committee = Committee(committee_id="C00000001")
for report in committee.select_efile_reports(min_receipt_date="2026-06-30", max_receipt_date="2026-10-16", sort="-receipt_date"):
    print(report.report_type, report.coverage_end_date, report.total_receipts_period)
```
`coverage_start_date`, `coverage_end_date` and `receipt_date` are timezone-aware `US/Eastern` datetimes, as on `Report`. A field missing from a result reads as `None`.

Requests are paced to one every 0.5 s process-wide (`pyopenfec.utils.MIN_REQUEST_INTERVAL`) and `OPENFEC_API_KEY` is read from the environment on each request. Every failure, including exhausted retries, is raised as `pyopenfec.utils.PyOpenFecException`.

## Development

```shell
poetry install
```

## Testing

```shell
OPENFEC_API_KEY=yourkey poetry run pytest
```