from book import Book
from book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Broker
import pnl


class MMParams:
    min_levels = 5
    liq_behind_exit = 0.1
    liq_behind_entry = BipolarContainer(Decimal(2), Decimal(1))
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
        Side.apply_sides(lambda side: self.engine.broker.cancel(0, side))
        exit_side = Side.opposite_side(self.engine.pnl.position())
        price = calc_price(self.engine.book.quote(exit_side), MMParams.liq_behind_exit)

        min_acceptable_price = self.specific_margin_price(
            self.engine.pnl.last_traded_price(),
            self.engine.pnl.last_traded_side(), Decimal(0.1))

        if (price - min_acceptable_price) / abs(price - min_acceptable_price) == Side.sign(exit_side):
            price = min_acceptable_price

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

    def specific_margin_price(self, entry_price, entry_side, margin, entry_commisiion=0, exit_commision=0):
        return entry_price \
               + Side.sign(entry_side) * (margin + entry_commisiion) \
               - Side.sign(entry_side) * exit_commision


# mm = Marketmaker(None)
# bid_price = Decimal(1109.785)
# print(mm.specific_margin_price(bid_price, Side.BID, Decimal('1')))
# ask_price = 1000
# print(mm.specific_margin_price(bid_price, Side.ASK, Decimal('0.1')))