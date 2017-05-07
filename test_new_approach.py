from decimal import Decimal

from instant_simulator import gen_book
from new_approach import hedge_positon_size, bound_to_lower_quote
from posmath.position import Position
from posmath.side import Side


def test_hedge_order():
    position = Position(side=Side.BID, price=Decimal('1500'), pos=Decimal('0.01'))
    hedge_pos = hedge_positon_size(position, Decimal('1500') * Decimal('1.01'), Decimal('0.01'))
    print(hedge_pos)
    print(position + hedge_pos)


def test_stick_to_quote():
    book = gen_book()
    position = Position(pos='0.01', price='1200', side=Side.BID)
    bound_to_lower_quote(book.quote(position.side()), position)

test_hedge_order()