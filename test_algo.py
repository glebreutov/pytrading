import random

import time
from book import Book
from posmath.side import Side
from mm.orders import Broker
import pnl


class MMParams:
    min_levels = 10
    liq_behind_exit = 1
    liq_behind_entry = 2
    order_size = 0.01


def calc_price(quote, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price


class TestReplace:

    def __init__(self, engine):
        self.engine = engine
        engine.book.quote_subscribers.append(self)

    def enter_market(self):
        self.engine.execution.request(
                tag=0,
                side=Side.BID,
                #price=calc_price(self.engine.book.quote(Side.ASK), MMParams.liq_behind_entry),
                price= 500 + random.randrange(0, 3),
                size=MMParams.order_size)

    def exit_market(self):
        Side.apply_sides(lambda side: self.engine.broker.cancel(0, side))
        exit_side = Side.opposite_side(self.engine.pnl.position())
        price = calc_price(self.engine.book.quote(exit_side), MMParams.liq_behind_exit)
        self.engine.broker.request(1, exit_side, price, self.engine.pnl.abs_position)

    def tick(self):
        if self.engine.pnl.position() == 0:
            self.enter_market()
        else:
            self.exit_market()

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()


class TestCancel:
    def __init__(self, engine):
        self.timer = time.time()
        self.engine = engine
        engine.book.quote_subscribers.append(self)
        self.enter = True

    def enter_market(self):
            self.engine.execution.request(
                tag=0,
                side=Side.BID,
                # price=calc_price(self.engine.book.quote(Side.ASK), MMParams.liq_behind_entry),
                price=500 + random.randrange(0, 3),
                size=MMParams.order_size)

    def exit_market(self):
        self.engine.execution.cancel_all()

    def tick(self):
        def time_is_up():
            return time.time() - self.timer > 10

        if self.enter and time_is_up():
            self.enter_market()
            self.enter = False
            self.timer = time.time()
        elif not self.enter and time_is_up():
            self.exit_market()
            self.enter = True
            self.timer = time.time()

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()


class TestExec:
    def __init__(self, engine):
        self.timer = time.time()
        self.engine = engine
        engine.book.quote_subscribers.append(self)
        self.placed = False


    def tick(self):
        bid_quote = self.engine.book.quote(Side.BID)
        ask_quote = self.engine.book.quote(Side.ASK)
        if not self.placed and min(bid_quote.levels(), ask_quote.levels()) > MMParams.min_levels:
            self.engine.execution.request(
                tag=0,
                side=Side.BID,
                price=self.engine.book.quote(Side.BID).price,
                #price=500 + random.randrange(0, 3),
                size=MMParams.order_size)
            self.placed = True

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()