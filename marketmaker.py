from book import Book
from book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Broker
import pnl


class MMParams:
    min_levels = 5
    liq_behind_exit = 0.3
    liq_behind_entry = BipolarContainer(Decimal(0.5), Decimal(0.3))
    order_size = 0.01


def calc_price(quote, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price


class Marketmaker:

    def __init__(self, engine):
        self.engine = engine
        engine.book.quote_subscribers.append(self)

    def enter_market(self):

        bid_quote = self.engine.book.quote(Side.BID)
        ask_quote = self.engine.book.quote(Side.ASK)
        if min(bid_quote.volume(), ask_quote.volume()) >= MMParams.liq_behind_entry.bid() \
            and min(bid_quote.levels(), ask_quote.levels()) > MMParams.min_levels:
            for side in Side.sides:
                    self.engine.execution.request(
                            tag=0,
                            side=side,
                            price=calc_price(self.engine.book.quote(side), MMParams.liq_behind_entry.side(side)),
                            size=str(MMParams.order_size))

    def exit_market(self):
        print("placing exit order")
        #Side.apply_sides(lambda side: self.engine.broker.cancel(0, side))
        self.engine.execution.cancel_all()
        exit_side = Side.opposite_side(self.engine.pnl.position())
        price = calc_price(self.engine.book.quote(exit_side), MMParams.liq_behind_exit)
        self.engine.execution.request(1, exit_side, price, str(self.engine.pnl.abs_position()))

    def tick(self):
        if self.engine.pnl.position() == 0:
            self.enter_market()
        else:
            self.exit_market()

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()