# AGENTS.md — AI & Coding Assistant Guide for pyopenfec

This is National Journal's fork of `pyopenfec`, a thin client for the OpenFEC
API. It is consumed by `nj-cms` (pinned by git tag in `NJ/requirements.txt`)
and by one-off scripts in `nj-scripts`. Changes here ship by tagging a release
and bumping that pin, so every change must be small, backwards compatible and
reviewable in one sitting.

Assistants and reviewers treat the constraints below as the rules for this
repo. If something is not written here, follow the surrounding code.

## 1. Project layout

- `pyopenfec/utils.py` — shared transport: `PyOpenFecApiClass` (and the
  paginated/indexed subclasses), `_throttled_request`, `BoundedRetry`,
  `TimeoutHTTPAdapter`, `PyOpenFecException`, `set_instance_attr`.
- `pyopenfec/<resource>.py` — one module per API resource (`candidate.py`,
  `committee.py`, `filing.py`, `report.py`, `efile_report.py`,
  `aggregates.py`, `transaction.py`). A resource class declares every known
  response field as an attribute defaulting to `None` in `__init__`, then
  sets whatever the API returned.
- `pyopenfec/__init__.py` — the public import surface. Export new resources
  and add them to `__all__`.
- `tests/` — `unittest.TestCase` style, run with `pytest`.
- `pyproject.toml` — poetry metadata and the version. `setup.cfg` — flake8.

## 2. How to work here

- Keep diffs minimal and surgical. Do not refactor, reformat or "clean up"
  code you were not asked to touch, and do not auto-fix lint unrelated to the
  task.
- Match the surrounding style and patterns, even where they differ from
  general best practice.
- Atomic commits with clear, specific messages. Formatting-only changes go in
  their own commit.
- Branch names are `<issue>-<short-desc>` (e.g. `8609-improve-fec-rate-limit-handling`).
  Issues are disabled on this repo; the number is the `nj-cms` issue the
  change supports. Reference it in the PR, but never write `Fixes #N`.
- Out-of-scope findings go in a PR comment or a new ticket, not in the diff.
- Never commit secrets or API keys. Do not edit `.gitignore` unless asked.
- Never push, tag, or open a PR unless asked.

## 3. Hard constraints

1. **No new runtime dependencies.** `requests` and `pytz` are the only
   runtime dependencies; do not add to `[tool.poetry.dependencies]`.
2. **Python 3.5-compatible syntax.** `pyproject.toml` declares
   `python = "^3.5"`. No f-strings, no walrus, no positional-only params, no
   `from __future__ import annotations`, no type annotations in signatures.
   Use `str.format()` / `%` like the surrounding code.
3. **flake8 clean at 120 columns** (`setup.cfg`). Run
   `flake8 pyopenfec tests` before declaring done.
4. **`PyOpenFecException` is the only error callers see.** Every failure in
   the request path (non-200 status, exhausted retries, transport errors,
   undecodable body, missing API key) must be raised as
   `pyopenfec.utils.PyOpenFecException`. Never let `requests`, `urllib3` or
   `json` exceptions escape a public method.
5. **Tests run offline.** New tests must not touch the network. Mock at or
   below the `requests.Session` boundary and feed genuine
   `requests.Response` objects (or genuine `http.client` responses) so
   status handling, JSON decoding and retry logic are exercised for real.
   Never require `OPENFEC_API_KEY` to be set to run a test. (The pre-existing
   `tests/test_candidate.py` and `tests/test_committee.py` hit the live API;
   do not copy that pattern and do not extend them.)
6. **No sleeping in tests.** Patch `time.sleep` (and the pacing clock) so the
   suite stays fast; assert on the sleep calls instead.
7. **Never log or print the API key.** It travels only as the `api_key`
   query parameter and is scrubbed from error messages.
8. **Backwards compatible public API.** Do not rename or remove existing
   classes, methods, attributes or the `fetch`/`fetch_one`/`count` contract.
   New behaviour is additive.
9. **Match the existing conventions.** Resource classes subclass the right
   base (`PyOpenFecApiPaginatedClass` for page-numbered endpoints,
   `PyOpenFecApiIndexedClass` for `last_index` endpoints), declare fields
   as `None` defaults, and `Committee`'s `select_*`/`all_*` helpers wrap the
   resource's `fetch` and are decorated with `utils.default_empty_list`.
10. **Version bump with the change.** A change that will be released bumps
    `version` in `pyproject.toml` (patch for additive changes). Tags on
    `master` use the bare version string (`0.2.10`), not a `v` prefix.
11. **No AI attribution** in commits, PR text, comments or code.

## 4. Conventions worth knowing

- `_make_request` builds `BASE_URL + VERSION + "/<resource>/"`, adds the API
  key (read from `OPENFEC_API_KEY` at call time), paces the request, raises
  on non-200 and returns the decoded JSON. Paginated `fetch` walks
  `pagination.pages`.
- A resource whose URL is not `"<classname>s"` passes `resource=` to
  `fetch`, as `Committee.select_reports` does, or overrides `fetch` to
  default it, as `EfileReport` does.
- Date handling is per-resource: a resource that wants tz-aware datetimes
  lists the fields in its `date_fields` and routes assignment through
  `utils.set_instance_attr`. Fields not listed keep the API's string.
- Logging goes through the root `logging` module at DEBUG for routine
  traffic and WARNING for things an operator should act on.

## 5. Testing

```shell
# from the repo root, in an environment with requests, pytz, pytest, flake8
pytest tests/test_efile_report.py tests/test_transport.py -q
flake8 pyopenfec tests
```

The live-API tests (`tests/test_candidate.py`, `tests/test_committee.py`)
need `OPENFEC_API_KEY` and network access; run them deliberately, not by
default.

## 6. Release

1. Merge to `master`.
2. Tag the merge commit with the bare version (`git tag 0.2.11`), push the tag.
3. Bump the pin in `nj-cms/NJ/requirements.txt` and rebuild the image.
