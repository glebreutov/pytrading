from book import Book
from book import Side
from mm.orders import Broker
import pnl


class MMParams:
    liq_behind_exit = 0.01
    liq_behind_entry = 0.1
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
        for side in Side.sides:
            if self.engine.book.quote(side).volume() > MMParams.liq_behind_entry:
                self.engine.execution.request(
                        tag=0,
                        side=side,
                        price=calc_price(self.engine.book.quote(side), MMParams.liq_behind_entry),
                        size=MMParams.order_size)
        # Side.apply_sides(
        #     lambda side: self.engine.execution.request(
        #         tag=0,
        #         side=side,
        #         price=calc_price(self.engine.book.quote(side), MMParams.liq_behind_entry),
        #         size=MMParams.order_size)
        # )

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