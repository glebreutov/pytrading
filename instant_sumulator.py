from decimal import Decimal

from book import Book
from posmath.side import Side
from orders import Broker, OrderManager
from pnl import PNL
from posmath.position import Position


def simulator_env(func, pos=Position(pos=0, balance=0), book_median=1000):
    pandl = PNL('0.3')
    book = Book()
    book.quote_subscribers.append(pandl)
    broker = Broker(OrderManager())
    pandl.execution(pos.side(), abs(pos.position()), abs(pos.price()))

    for i in range(0, 6):
        book.increment_level(Side.ASK, Decimal(book_median + 10 + i), Decimal(i / 100))
        book.increment_level(Side.BID, Decimal(book_median - 10 - i), Decimal(i / 100))
        book.quote_changed(Side.BID)
        book.quote_changed(Side.ASK)

    return func(book, pandl, broker)