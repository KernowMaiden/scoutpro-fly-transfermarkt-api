"""
Regression guard for the Transfermarkt day-first date fault, 5 November 2026.

Transfermarkt serves numeric dates DAY FIRST. `TransfermarktBaseModel.parse_str_to_date` hands the
string to `dateutil.parser.parse`, whose default is `dayfirst=False`, so "01/07/2026" was read as
7 January 2026. Because dateutil is LENIENT, "25/08/2026" was still coerced correctly, which
confined the fault to dates whose day is 12 or less. In the consuming database that produced 4,756
wrong rows of 10,963, with 3,437 of them landing on 7 January: 1 July is contract-expiry and
age-group promotion day, so it is the single most common real transfer date there is.

These tests need no network.
"""

import pytest
from dateutil import parser

from app.schemas.players.transfers import PlayerTransfer
from app.utils.utils import find_ddmmyyyy


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("01/07/2026", "2026-07-01"),  # the fault: 1 July, previously read as 7 January
        ("01/09/2026", "2026-09-01"),
        ("06/07/2026", "2026-07-06"),
        ("03/09/2026", "2026-09-03"),
        ("25/08/2026", "2026-08-25"),  # unambiguous, was already correct, must stay correct
        ("30/06/2026", "2026-06-30"),  # the other half of the same contract event
        ("31/05/2026", "2026-05-31"),
        ("1/7/2026", "2026-07-01"),  # unpadded
        ("01.07.2026", "2026-07-01"),  # dot separator
        ("01-07-2026", "2026-07-01"),  # dash separator
        ("24/06/1987 (39)", "1987-06-24"),  # the profile dob shape, with a trailing age
    ],
)
def test_day_first_numeric_dates_become_iso(raw, expected):
    """A day-first numeric date is normalised to ISO, whether or not it is ambiguous."""
    assert find_ddmmyyyy(raw) == expected


@pytest.mark.parametrize("raw", ["-", "", None, "Jul 1, 2026", "2026-07-01", "unknown", "13/13/2026"])
def test_anything_not_a_day_first_date_is_left_alone(raw):
    """
    Returns None for anything it cannot read day-first, so the caller falls through to the original.

    This is the control that keeps the fix from becoming a regression: a textual date, an ISO date
    and "-" must NOT be rewritten, because dateutil already handles those correctly. "13/13/2026"
    covers an impossible month.
    """
    assert find_ddmmyyyy(raw) is None


def test_the_fault_is_real_and_the_fix_removes_it():
    """
    The negative control, stated as the before and after of one string.

    Without the normalisation the old path really did produce 7 January, and with it the value is
    1 July. A test that only asserted the fixed value could pass against a parser that never had
    the bug, so both arms are here.
    """
    raw = "01/07/2026"
    assert parser.parse(raw).date().isoformat() == "2026-01-07"  # the fault, reproduced
    assert find_ddmmyyyy(raw) == "2026-07-01"  # the fix


def test_the_model_emits_the_corrected_date_and_keeps_the_original():
    """End to end through the real Pydantic model, with the payload shaped as the service builds it."""
    raw = "01/07/2026"
    transfer = PlayerTransfer(
        id="6296358",
        clubFrom={"id": "1", "name": "Yeovil Town"},
        clubTo={"id": "2", "name": "Brackley"},
        date=find_ddmmyyyy(raw) or raw,
        dateRaw=raw,
        upcoming=False,
        season="26/27",
        marketValue=None,
        fee=None,
    )
    assert transfer.date.isoformat() == "2026-07-01"
    assert transfer.date_raw == "01/07/2026"
    assert transfer.season == "26/27"  # and now the date sits inside the season TM itself reported
