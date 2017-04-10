from functools import reduce

from decimal import Decimal

from posmath.side import Side
from mm.orders import OrderStatus


def print_book_and_orders(book, broker):
    def print_side(side):
        levels = []
        book.quote(side).print_side(levels)

        orders = [o for o in broker.orders.side(side).values() if o is not None and o.status != OrderStatus.COMPLETED]
        prices = sorted(set([l.price for l in levels])| set([o.price for o in orders]))

        for p in prices:
            try:
                vol = max(filter(lambda l: l.price == p, levels)).size
            except ValueError:
                vol = Decimal('0')
            try:
                o = max(filter(lambda l: l.price == p, orders)).amount
            except ValueError:
                o = ''

            print(side + "\t" + "{:>10.8}".format(p) + "\t" + "{:>10.2}".format(vol) + "\t" + "{:>10.2}".format(o))


    print_side(Side.BID)
    print('--------')
    print_side(Side.ASK)