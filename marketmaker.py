from decimal import Decimal

import time

from mm.exit_strategy import calc_price, calc_price_between_levels, price_on_a_depth
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
        self.last_updated_time = time.time()
        self.engine = engine
        self.config = MMParams(config)
        # engine.book.quote_subscribers.append(self)

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

    def price_changed(self, tag, side, new_price, size):
        order = self.engine.execution.order(tag, side)
        if order is None or order.status == OrderStatus.COMPLETED:
            return True

        if order.amount != size:
            return True

        return abs(order.price - new_price) > self.config.price_tolerance

    def enter_market(self):

        for side in Side.sides:
            if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.EXIT_TAG):
                self.engine.execution.order(Marketmaker.ENTER_TAG, side)
                size = adjusted_size(self.config.order_sizes.side(side), side, self.engine.pnl.position())
                price = price_on_a_depth(self.engine.book.quote(side), self.config.liq_behind_entry.side(side), size)
                if self.price_changed(Marketmaker.ENTER_TAG, side, price, size) and size >= self.config.min_order_size:
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
        def should_loss():
            return self.engine.rm.loss_flag_time > self.engine.pnl.zero_position_time

        for side in Side.sides:
            self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
        if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.ENTER_TAG):

            exit_position, method = stop_loss_exit_strategy(self.engine.book, self.engine.pnl,
                                                            self.config, should_loss())
            price_or_size = self.price_changed(Marketmaker.EXIT_TAG, exit_position.side(), exit_position.price(),
                                               exit_position.abs_position())
            if self.engine.pnl.abs_position() >= self.config.min_order_size \
                    and price_or_size:
                self.engine.execution.request(Marketmaker.EXIT_TAG, exit_position.side(), exit_position.price(),
                                              str(exit_position.abs_position()))
                self.engine.pnl.update_open_pnl(exit_position.price())
                self.engine.pnl.set_exit_method(method)

    def on_tick(self):
        risk_status = self.engine.rm.status
        if risk_status == RiskManager.CANCEL_ALL:
            self.engine.execution.cancel_all()
        elif risk_status == RiskManager.EXIT_ONLY:
            self.exit_market()
        elif risk_status == RiskManager.NORMAL:
            if self.engine.pnl.abs_position() < self.config.min_order_size:
                self.enter_market()
            else:
                self.exit_market()

    # def quote_changed(self, side):
    #     self.on_tick()

    def on_md(self):
        if time.time() - self.last_updated_time >= 1:
            self.on_tick()
            self.last_updated_time = time.time()

    def on_exec(self, details):
        self.on_tick()

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.GAP:
            for side in Side.sides:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
