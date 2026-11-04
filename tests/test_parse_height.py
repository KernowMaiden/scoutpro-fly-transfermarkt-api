"""The height validator, tested on the value it produces rather than the string
it was given.

This bug survived because the existing suite asserts the SCRAPED SHAPE and not
the conversion: `tests/conftest.py` checks `height` against
`^(\\d+,\\d+m)|(m)$`, which is a claim about what Transfermarkt's page looks
like. Every one of those assertions passed while the parsed value was wrong,
because nothing ever looked at the integer.

Transfermarkt renders height as metres with a decimal comma, "1,80 m", on
English pages as well. The old implementation deleted the comma and kept the
digits:

    int(v.replace(",", "").replace("m", "").replace("،", ""))

which is right for a TWO-decimal source by luck ("1,78 m" -> 178) and wrong for
a ONE-decimal source ("1,7 m" -> 17). That asymmetry is why it went unnoticed:
only the one-decimal players ever looked broken, so the damage presented as a
handful of odd rows rather than as a broken conversion.

Verified against three live Transfermarkt pages, 4 Nov 2026:

    tm 1170685  Thierry Rohart-Brown   "Height: 1,7 m"   stored 17
    tm 1333346  Jay Henderson          "Height: 1,8 m"   stored 18
    tm 1164755  Eran Ginat             "Height: 1,8 m"   stored 18
"""

from typing import Optional

import pytest

from app.schemas.base import TransfermarktBaseModel


class _Probe(TransfermarktBaseModel):
    height: Optional[int] = None


@pytest.mark.parametrize(
    "raw,expected",
    [
        # One decimal: the case that was wrong, and the one that put real
        # footballers into a database at 17cm and 18cm tall.
        ("1,7 m", 170),
        ("1,8 m", 180),
        ("1,9 m", 190),
        # Two decimals: these were already right, by luck rather than by
        # design, and must stay right.
        ("1,78 m", 178),
        ("1,80 m", 180),
        ("1,90 m", 190),
        ("2,06 m", 206),
        # No space before the unit, and no unit at all.
        ("1,80m", 180),
        ("1,80", 180),
        # Arabic decimal separator, which the original handled and so must this.
        ("1,80‎ m", 180),
        # Absent or non-numeric: None, never 0. A zero height would read as a
        # measurement and pass every range check.
        ("", None),
        ("-", None),
        ("- ", None),
        (None, None),
    ],
)
def test_parse_height(raw, expected):
    assert _Probe(height=raw).height == expected


def test_no_plausible_height_is_mangled():
    """A sanity sweep over the real range, asserting the round trip.

    The point is the POPULATION rather than the individual cases above: every
    height a footballer can have, written the way Transfermarkt writes it, must
    come back as the centimetres it means. The old implementation fails this at
    every single one-decimal value, which is 11 of the 101.
    """
    for cm in range(150, 211):
        metres = f"{cm / 100:.2f}".replace(".", ",") + " m"
        assert _Probe(height=metres).height == cm, metres

    # And the one-decimal spellings, which is where it actually broke.
    # 1,5 m through 2,0 m, i.e. 150cm to 200cm.
    for d in range(15, 21):
        metres = f"{d / 10:.1f}".replace(".", ",") + " m"
        assert _Probe(height=metres).height == d * 10, metres
