from mm.book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Exec


class SidePnl:
    def __init__(self):
        self.position = Decimal(0)
        self.pending = 0
        self.quote_price = 0
        self.last_price = 0


class PNL:
    def __init__(self, fee):
        self.pnl = BipolarContainer(SidePnl(), SidePnl())
        self.position_cost = Decimal('0')
        self.closed_pnl = Decimal('0')
        self.exit_price = Decimal('0')
        self.fee = Decimal(fee)

    def execution(self, side, delta, price):
        if delta > 0:
            side_pnl = self.pnl.side(side)
            side_pnl.position += abs(delta)
            side_pnl.last_price = price
            self.pnl.side(Side.opposite(side)).last_price = 0
            self.position_cost += -Side.sign(side) * delta * price

        if self.position() == 0:
            self.closed_pnl += self.position_cost
            self.position_cost = 0

    def position(self):
        return self.pnl.bid().position - self.pnl.ask().position

    def abs_position(self):
        return abs(self.position())

    def quote_changed(self, quote):
        self.pnl.side(quote.side).quote_price = quote.price

    def balance(self):
        return self.position_cost

    def last_traded_price(self):
        return max(self.pnl.ask().last_price, self.pnl.bid().last_price)

    # def last_traded_side(self):
    #     return Side.ASK if self.pnl.ask().last_price > 0 else Side.BID

    def open_pnl(self):
        return self.balance() + self.position() * self.exit_price

    def update_open_pnl(self, exit_price):
        self.exit_price = exit_price

    def nbbo_pnl(self):
        exit_side = Side.opposite_side(self.position())
        exit_nbbo = self.pnl.side(exit_side).quote_price

        delta = (self.position_zero_price() - exit_nbbo) * self.abs_position()
        return delta * Side.sign(exit_side)

    def take_pnl(self):
        exit_side = Side.opposite_side(self.position())
        exit_nbbo = self.pnl.side(Side.side(self.position())).quote_price

        delta = (self.position_zero_price() - exit_nbbo) * self.abs_position()
        return delta * Side.sign(exit_side) - (delta / 100 * self.fee)

    def position_zero_price(self):
        if self.abs_position() == 0:
            return 0
        else:
            return abs(self.balance() / self.abs_position())

    def position_side(self):
        return Side.side(self.position())