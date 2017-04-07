from functools import reduce

from posmath.side import Side
from mm.orders import OrderStatus


def print_book_and_orders(book, broker):
    def print_side(side):
        levels = []
        book.quote(side).print_side(levels)
        orders = filter(lambda o: o is not None and o.status != OrderStatus.COMPLETED, broker.orders.side(side).values())

        def f(a, x):
            a[x.price] = x

        order_dict = {}
        reduce(f, orders, order_dict)

        start = 0 if side == Side.ASK else len(levels) - 10
        stop = 9 if side == Side.ASK else len(levels)
        for lvl in levels[start:stop]:
            r = lvl.__str__()
            if lvl.price in order_dict:
                r += '| ' + str(order_dict[lvl.price].pending)
            print(r)

    print_side(Side.BID)
    print('--------')
    print_side(Side.ASK)