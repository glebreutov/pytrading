from posmath.position import Position
from posmath.side import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import Exec


class PNL:
    def __init__(self, fee):
        self.method = "NONE"
        self.pos = Position(0, 0)
        self.nbbo = BipolarContainer(0, 0)
        self.closed_pnl = Decimal('0')
        self.exit_price = Decimal('0')
        self.fee = Decimal(fee)

    def execution(self, side, delta, price):
        if delta > 0:
            self.pos += Position(pos=delta, price=price, side=side)

        if self.pos.position() == 0:
            self.closed_pnl += self.pos.balance

    def position(self):
        return self.pos.position()

    def abs_position(self):
        return self.pos.abs_position()

    def quote_changed(self, quote):
        self.nbbo.set_side(quote.side, quote.price)

    def balance(self):
        return self.pos.balance

    def open_pnl(self):
        return self.balance() + self.position() * self.exit_price

    def update_open_pnl(self, exit_price):
        self.exit_price = exit_price

    def nbbo_pnl(self):
        exit_side = Side.opposite_side(self.position())
        nbbo_price = self.nbbo.side(exit_side)
        return (self.pos + Position(pos=self.pos.abs_position(), price=nbbo_price, side=exit_side)).balance

    def take_pnl(self):
        if self.pos.position() == 0:
            return Decimal('0')
        exit_side = Side.opposite_side(self.position())
        take_price = self.nbbo.side(Side.side(self.position()))

        balance = (self.pos + Position(pos=self.pos.abs_position(), price=take_price, side=exit_side)).balance
        return balance - abs(balance) / Decimal('100') * self.fee

    def position_zero_price(self):
        if self.abs_position() == 0:
            return Decimal('0')
        else:
            return abs(self.balance() / self.abs_position())

    def position_side(self):
        return Side.side(self.position())

    def set_exit_method(self, method):
        self.method = method

    def exit_method(self):
        return self.method
