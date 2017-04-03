import json
from copy import copy
from decimal import Decimal

from book import Side, Book, Level
from marketmaker import MMParams
from orders import Order, Broker, OrderManager, Ack
from pnl import PNL
from printout import print_book_and_orders


class Position:
    def __init__(self, pos, cost):
        self.balance = cost
        self.pos = pos

    def position(self):
        return self.pos

    def abs_position(self):
        return abs(self.pos)

    def side(self):
        return Side.side(self.pos)

    def opposite(self):
        return Position(-1 * self.pos, -1 * self.balance)

    def price(self):
        if self.pos == 0:
            return 0

        return round(abs(self.balance / self.pos), 4)

    def add(self, side, size, price):
        sign = Side.sign(side) *-1
        return Position(self.pos + sign * size, self.balance - sign * size * price)

    def add_pos(self, opposition):
        return Position(self.pos + opposition.pos, self.balance + opposition.balance)

    def margin(self, margin):
        return Position(self.pos, self.balance + margin)

    def pnl(self, side, size, price):
        return self.add(side, size, price).balance

    def oppoiste_with_price(self, price):
        return Position(-self.pos, price * self.pos)

    def opposite_with_margin(self, margin):
        return self.opposite().margin(margin)

    def __str__(self):
        return json.dumps(
            {'balance': str(self.balance),
             'position': str(self.position()),
             'side': self.side(),
             'price': str(self.price())})


def remove_price(quote: Level, pos):
    last_price = 0
    while pos.abs_position() != 0:
        if pos.abs_position() > quote.size:
            pos = pos.add(quote.side, quote.size, quote.price)
        else:
            pos = pos.add(quote.side, pos.abs_position(), quote.price)
        last_price = last_price
        if quote.next_level is not None:
            quote = quote.next_level
        elif pos.abs_position():
            raise RuntimeError

    return pos, last_price


def exit_price_strategy(book: Book, pos: Position, config: MMParams):
    # pos, last_price = remove_price(book.quote(pos.side()), pos)
    # if pos.balance > 0:
    #     remove_pos = pos.oppoiste_with_price(last_price)
    remove_pos = pos.oppoiste_with_price(book.quote(pos.side()).price)
    add_pos = pos.oppoiste_with_price(book.quote(Side.opposite(pos.side())).price)
    if pos.add_pos(remove_pos).balance > 0:
        return remove_pos
    elif pos.add_pos(add_pos).balance > 0:
        return add_pos
    else:
        return pos.opposite_with_margin(config.min_profit)


def test_exit_price_strategy_3d():
    def test_with_params(pos: Position):
        pandl = PNL('0.3')
        book = Book()
        book.quote_subscribers.append(pandl)
        config = MMParams({
            "min_levels": "5",
            "liq_behind_exit": "0.02",
            "liq_behind_entry": {"BID": "0.41", "ASK": "0.41"},
            "order_sizes": {"BID": "0.07", "ASK": "0.07"},
            "min_profit": "0.01",
            "min_order_size": "0.01",

            "taker_exit_profit": "0.1"
        })
        pandl.execution(pos.side(), abs(pos.position()), abs(pos.price()))
        median = 1000
        for i in range(0, 6):
            book.increment_level(Side.ASK, Decimal(median + 10+i), Decimal(i / 100))
            book.increment_level(Side.BID, Decimal(median - 10-i), Decimal(i / 100))
            book.quote_changed(Side.BID)
            book.quote_changed(Side.ASK)

        broker = Broker(OrderManager())

        start_position = Position(pandl.position(), pandl.balance())
        print("before "+str(start_position))
        exit_order = exit_price_strategy(book, start_position, config)
        pandl.execution(exit_order.side(), exit_order.abs_position(), exit_order.price())
        broker.request(0, exit_order.side(), exit_order.price(), exit_order.abs_position())
        keys = broker.om.by_oid.keys()
        tmp = ''
        for x in keys:
            tmp = x

        broker.om.on_ack(Ack(tmp, 1, start_position.abs_position(), start_position.abs_position()))
        print_book_and_orders(book, broker)
        print("after " + str(exit_order))
        assert pandl.closed_pnl > 0
        return exit_order

    #remove
    prior_pos = Position(Decimal('0.07'), Decimal('-900') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('989')
    assert eo.side() == Side.ASK
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0
    prior_pos = Position(Decimal('-0.07'), Decimal('1100') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('1011')
    assert eo.side() == Side.BID
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0
    #quote
    prior_pos = Position(Decimal('0.07'), Decimal('-1010') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('1011')
    assert eo.side() == Side.ASK
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0
    prior_pos = Position(Decimal('-0.07'), Decimal('990') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('989')
    assert eo.side() == Side.BID
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0
    #min profit
    prior_pos = Position(Decimal('0.07'), Decimal('-1013') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('1013.1429')
    assert eo.side() == Side.ASK
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0

    prior_pos = Position(Decimal('-0.07'), Decimal('900') * Decimal('0.07'))
    eo = test_with_params(prior_pos)
    assert eo.price() == Decimal('899.8571')
    assert eo.side() == Side.BID
    pos = prior_pos.add_pos(eo)
    print("reminder " + str(pos))
    assert pos.balance > 0

test_exit_price_strategy_3d()
