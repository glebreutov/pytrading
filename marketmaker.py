from decimal import Decimal

from mm.exit_strategy import calc_price, calc_price_between_levels
from mm.event_hub import ImportantEvent
from mm.exit_strategy import stop_loss_exit_strategy
from mm.orders import RiskManager, OrderStatus
from mm.mmparams import MMParams
from posmath.position import Position
from posmath.side import Side


def should_update_price(side, current_price: Decimal, new_price: Decimal, barrier: Decimal):
    return current_price - new_price > barrier or Side.closer_to_quote(side, current_price, new_price) == new_price


def adjusted_size(order_size, order_side, pos):
    pos_side = Side.side(pos)
    if pos_side == order_side:
        return order_size - abs(pos)
    else:
        return order_size + abs(pos)


class Marketmaker:
    ENTER_TAG = 0
    EXIT_TAG = 1

    def __init__(self, engine, config):
        self.engine = engine
        self.config = MMParams(config)
        engine.book.quote_subscribers.append(self)

    def book_is_valid(self):
        bid_quote = self.engine.book.quote(Side.BID)
        ask_quote = self.engine.book.quote(Side.ASK)
        return bid_quote is not None \
               and ask_quote is not None \
               and min(bid_quote.volume(), ask_quote.volume()) >= self.config.liq_behind_entry.bid() \
               and min(bid_quote.levels(), ask_quote.levels()) > self.config.min_levels

    def no_orders_for_tag(self, tag):
        bo = self.engine.execution.order(tag, Side.BID)
        so = self.engine.execution.order(tag, Side.ASK)
        return (bo is None or bo.status == OrderStatus.COMPLETED) \
               and (so is None or so.status == OrderStatus.COMPLETED)

    def enter_market(self):
        def price_changed(tag, side, new_price):
            order = self.engine.execution.order(tag, side)
            if order is None:
                return True

            return abs(order.price - new_price) > self.config.price_tolerance

        for side in Side.sides:
            if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.EXIT_TAG):
                self.engine.execution.order(Marketmaker.ENTER_TAG, side)
                size = adjusted_size(self.config.order_sizes.side(side), side, self.engine.pnl.position())
                # price = calc_price(self.engine.book.quote(side), self.config.liq_behind_entry.side(side))
                price = calc_price_between_levels(self.engine.book.quote(side), self.config.liq_behind_entry.side(side),
                                                  Decimal('0.0001'))
                if price_changed(Marketmaker.ENTER_TAG, side, price) and size >= self.config.min_order_size:
                    self.engine.execution.request(
                        tag=Marketmaker.ENTER_TAG,
                        side=side,
                        price=price,
                        size=str(size)
                    )
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
                self.engine.pnl.set_exit_method("ENTER")
            else:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)

    def exit_market(self):
        # print("placing exit order")

        for side in Side.sides:
            self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
        if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.ENTER_TAG):

            position = Position(pos=self.engine.pnl.position(), balance=self.engine.pnl.balance())
            exit_position, method = stop_loss_exit_strategy(self.engine.book, position, self.config)
            if self.engine.pnl.abs_position() >= self.config.min_order_size:
                self.engine.execution.request(Marketmaker.EXIT_TAG, exit_position.side(), exit_position.price(),
                                              str(exit_position.abs_position()))
                self.engine.pnl.update_open_pnl(exit_position.price())
                self.engine.pnl.set_exit_method(method)

    def tick(self):
        risk_status = self.engine.execution.rm.status
        if risk_status == RiskManager.CANCEL_ALL:
            self.engine.execution.cancel_all()
        elif risk_status == RiskManager.EXIT_ONLY:
            self.exit_market()
        elif risk_status == RiskManager.NORMAL:
            if self.engine.pnl.abs_position() < self.config.min_order_size:
                self.enter_market()
            else:
                self.exit_market()

    def quote_changed(self, side):
        self.tick()

    def on_exec(self, details):
        self.tick()

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.GAP:
            for side in Side.sides:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
