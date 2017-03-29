from _decimal import Decimal

from book import Side


def test_closer_to_quote():
    assert Side.closer_to_quote(Side.BID, 10, 11) == 11
    assert Side.closer_to_quote(Side.ASK, 10, 11) == 10
    assert Side.closer_to_quote(Side.ASK, 10, 10) == 10
    assert Side.closer_to_quote(Side.BID, 11, 11) == 11

    assert Side.closer_to_quote(Side.BID, 10.01, 11.01) == 11.01
    assert Side.closer_to_quote(Side.ASK, 10.01, 11.01) == 10.01
    assert Side.closer_to_quote(Side.ASK, 10.01, 10.01) == 10.01
    assert Side.closer_to_quote(Side.BID, 11.01, 11.01) == 11.01

    assert Side.closer_to_quote(Side.BID, Decimal(10.01), Decimal(11.01)) == 11.01
    assert Side.closer_to_quote(Side.ASK, Decimal(10.01), Decimal(11.01)) == 10.01
    assert Side.closer_to_quote(Side.ASK, Decimal(10.01), Decimal(10.01)) == 10.01
    assert Side.closer_to_quote(Side.BID, Decimal(11.01), Decimal(11.01)) == 11.01


test_closer_to_quote()