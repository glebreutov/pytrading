import time

from posmath.position import Position
from posmath.side import Side
from decimal import Decimal

from mm.book import BipolarContainer, Level
from mm.orders import Exec


class PNL:
    def __init__(self, fee):
        self.method = "NONE"
        self.pos = Position(0, 0)
        self.nbbo = BipolarContainer(0, 0)
        self.closed_pnl = Decimal('0')
        self.clean_closed_pnl = Decimal('0')
        self.exit_price = Decimal('0')
        self.fee = Decimal(fee)
        self.ema = 0
        self.zero_position_time = time.time()

    def execution(self, tx: Exec):
        exec_pos = Position(pos=tx.delta, price=tx.price, side=tx.side)
        if tx.delta > 0:
            self.pos += exec_pos + exec_pos.fee_pos(tx.fee)

        if self.pos.position() == 0:
            self.closed_pnl += self.pos.balance
            self.pos = Position(0, 0)
            self.zero_position_time = time.time()
            # self.clean_closed_pnl += self.closed_pnl
            # self.closed_pnl = 0

    def position(self):
        return self.pos.position()

    def abs_position(self):
        return self.pos.abs_position()

    def quote_changed(self, quote):
        self.nbbo.set_side(quote.side, quote.price)
        k = Decimal(2 / (40 + 1))
        if self.nbbo.bid() == 0 or self.nbbo.ask() == 0:
            return

        mid_price = (self.nbbo.bid() + self.nbbo.ask())/2
        if self.ema == 0:
            self.ema = mid_price
        else:
            self.ema = round(mid_price * k + self.ema * (1 - k), 4)

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
        take_order = Position(pos=self.pos.abs_position(), price=take_price, side=exit_side)
        take_pos = self.pos + take_order + take_order.fee_pos(self.fee)

        return take_pos.balance

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

