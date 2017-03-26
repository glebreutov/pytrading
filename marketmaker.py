from book import Book
from book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Broker
import pnl


class MMParams:
    min_levels = 5
    liq_behind_exit = 0.3
    liq_behind_entry = BipolarContainer(Decimal(0.6), Decimal(0.6))
    order_size = 0.03


def calc_price(quote, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price


def specific_margin_price(entry_price, entry_side, margin, entry_commisiion=0, exit_commision=0):
    return entry_price \
           + Side.sign(entry_side) * (margin + entry_commisiion) \
           - Side.sign(entry_side) * exit_commision


def exit_price(enter_side, enter_price, opposite_quote_price):
    min_acceptable_price = specific_margin_price(
        enter_price,
        enter_side, Decimal(str(0.1)))

    delta = opposite_quote_price - min_acceptable_price
    if delta != 0 and delta / abs(delta) != Side.sign(enter_side):
        opposite_quote_price = min_acceptable_price
    return opposite_quote_price


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
        for side in Side.sides:
            self.engine.execution.cancel(0, side)

        exit_side = Side.opposite_side(self.engine.pnl.position())
        quote_price = calc_price(self.engine.book.quote(exit_side), MMParams.liq_behind_exit)
        eprice = exit_price(self.engine.pnl.last_traded_side(), self.engine.pnl.last_traded_price(), quote_price)

        self.engine.execution.request(1, exit_side, eprice, str(self.engine.pnl.abs_position()))

    def tick(self):
        if not self.engine.execution.rm.exit_only() and self.engine.pnl.abs_position() < Decimal(str(0.01)):
            self.enter_market()
        else:
            self.exit_market()

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()






# print(exit_price(Side.BID, 100, 105))
# print(exit_price(Side.ASK, 105, 100))
#
# print(exit_price(Side.BID, 100, 90))
# print(exit_price(Side.ASK, 105, 110))

# mm = Marketmaker(None)
# bid_price = Decimal(1109.785)
# print(mm.specific_margin_price(bid_price, Side.BID, Decimal('1')))
# ask_price = 1000
# print(mm.specific_margin_price(bid_price, Side.ASK, Decimal('0.1')))