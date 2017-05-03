from decimal import Decimal
from random import randrange

from book import Book
from posmath.side import Side
from orders import Broker, OrderManager, Exec
from pnl import PNL
from posmath.position import Position


def gen_book(median=1300, spread=2, levels=10):
    def gen_prices(side):
        sign = -Side.sign(side)
        prev_price = Decimal(median + sign * spread / 2)

        for i in range(0, levels):
            next_price = prev_price + Decimal(sign * randrange(1, 1000, 1) / 1000)
            final_next_price = round(Decimal(next_price), 4)
            size = round(Decimal(randrange(1, 100, 1)/100), 2)
            yield final_next_price, size
            prev_price = final_next_price

    book = Book()

    def update_side(side):
        for price, size in gen_prices(side):
            book.increment_level(side, price, size)

    update_side(Side.ASK)
    update_side(Side.BID)

    return book


def simulator_env(func, pos=Position(pos=0, balance=0), book_median=1000):
    pandl = PNL('0.3')
    book = Book()
    book.quote_subscribers.append(pandl)
    broker = Broker(OrderManager())

    pandl.execution(pos.side(), abs(pos.position()), abs(pos.price()))

    for i in range(0, 6):
        book.increment_level(Side.ASK, Decimal(book_median + 10 + randrange()), Decimal(i / 100))
        book.increment_level(Side.BID, Decimal(book_median - 10 - i), Decimal(i / 100))
        book.quote_changed(Side.BID)
        book.quote_changed(Side.ASK)

    return func(book, pandl, broker)