from decimal import Decimal

from book import Book
from posmath.side import Side
from marketmaker import adjusted_size
from mmparams import MMParams
from order_algos import hold_exit_price_strategy
from orders import Broker, OrderManager
from pnl import PNL
from printout import print_book_and_orders


def test_adj_side():
    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('0.00')) == Decimal('0.07')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('0.00')) == Decimal('0.07')

    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('0.01')) == Decimal('0.06')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('0.01')) == Decimal('0.08')

    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('-0.01')) == Decimal('0.08')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('-0.01')) == Decimal('0.06')


def test_exit_price_strategy():
    def test_with_params(pos, enter_price):
        pnl = PNL('0.3')
        book = Book()
        book.quote_subscribers.append(pnl)
        config = MMParams({
            "min_levels": "5",
            "liq_behind_exit": "0.02",
            "liq_behind_entry": {"BID": "0.41", "ASK": "0.41"},
            "order_sizes": {"BID": "0.07", "ASK": "0.07"},
            "min_profit": "0.01",
            "min_order_size": "0.01",
            "buried_volume": "10",
            "taker_exit_profit": "0.1",
            "price_tolerance": "0.0005"
        })
        pnl.execution(Side.side(pos), abs(pos), abs(enter_price))
        median = 1000
        for i in range(0, 5):
            book.increment_level(Side.ASK, Decimal(median + i), Decimal(i / 100))
            book.increment_level(Side.BID, Decimal(median - i), Decimal(i / 100))
            book.quote_changed(Side.BID)
            book.quote_changed(Side.ASK)

        print_book_and_orders(book, Broker(OrderManager()))
        exit_price = hold_exit_price_strategy(book, pnl, config)
        pnl.execution(Side.opposite(pnl.position_side()), abs(pos), exit_price)

        return pnl.closed_pnl

    #take
    assert test_with_params(Decimal('0.07'), Decimal('60')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('200')) > 0
    #quote
    assert test_with_params(Decimal('0.07'), Decimal('77')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('77')) > 0
    #min profit
    assert test_with_params(Decimal('0.07'), Decimal('77')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('77')) > 0

