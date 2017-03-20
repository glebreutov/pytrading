from book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Exec


class SidePnl:
    def __init__(self):
        self.position = Decimal(0)
        self.pending = 0
        self.quote_price = 0


class PNL:
    def __init__(self):
        self.pnl = BipolarContainer(SidePnl(), SidePnl())

    def execution(self, details: Exec):
        side_pnl = self.pnl.side(details.side)
        side_pnl.position += abs(details.amount)
        side_pnl.last_price = details.price
        self.pnl.side(Side.opposite(details.side)).last_price = 0

    def position(self):
        return self.pnl.bid().position - self.pnl.ask().position

    def abs_position(self):
        return abs(self.position())

    def quote_changed(self, quote):
        self.pnl.side(quote.side).quote_price = quote.price

    def balance(self):
        return self.abs_position() * self.pnl.side(Side.opposite_side(self.position())).quote_price

    def last_traded_price(self):
        return max(self.pnl.ask().last_price, self.pnl.bid().last_price)

    def last_traded_side(self):
        return Side.ASK if self.pnl.ask().last_price > 0 else Side.BID