from decimal import Decimal

import time

from mm.app_config import AppConfig, MarketmakerConfig, VenueConfig

from mm.order_algos import price_on_a_depth, enter_ema, ema_constraint
from mm.event_hub import ImportantEvent
from mm.order_algos import stop_loss_exit_strategy
from mm.orders import RiskManager, OrderStatus
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

    def __init__(self, engine):
        self.last_updated_time = time.time()
        self.engine = engine
        self.config: MarketmakerConfig = self.engine.config.marketmaker
        self.venue_config: VenueConfig = self.engine.config.venue
        # engine.book.quote_subscribers.append(self)

    def book_is_valid(self):
        bid_quote = self.engine.book.quote(Side.BID)
        ask_quote = self.engine.book.quote(Side.ASK)
        return bid_quote is not None \
               and ask_quote is not None \
               and min(bid_quote.volume(), ask_quote.volume()) >= self.config.liq_behind.bid() \
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
        method_both = ""
        for side in Side.sides:
            if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.EXIT_TAG):
                pnl = self.engine.pnl
                quote = self.engine.book.quote(side)
                size = adjusted_size(self.config.order_size.side(side), side, pnl.position())

                depth_price = price_on_a_depth(self.engine.book.quote(side), size, self.config, self.venue_config)
                ema_price = enter_ema(quote=quote, ema=pnl.ema.calc_ema(), ac=self.config, vc=self.venue_config)
                price, method = ema_constraint(depth_price, ema_price, side)
                method_both = method + " " + method_both
                if self.price_changed(Marketmaker.ENTER_TAG, side, price, size) and size >= self.venue_config.min_order_size:
                    self.engine.execution.request(
                        tag=Marketmaker.ENTER_TAG,
                        side=side,
                        price=price,
                        size=str(size)
                    )
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
                pnl.set_exit_method(method_both)
            else:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)

    def exit_market(self):
        def should_loss():
            return self.engine.rm.loss_flag_time > self.engine.pnl.zero_position_time

        for side in Side.sides:
            self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
        if self.book_is_valid() and self.no_orders_for_tag(Marketmaker.ENTER_TAG):

            exit_position, method = stop_loss_exit_strategy(self.engine.book, self.engine.pnl,
                                                            self.config, self.venue_config, should_loss())
            price_or_size = self.price_changed(Marketmaker.EXIT_TAG, exit_position.side(), exit_position.price(),
                                               exit_position.abs_position())
            if self.engine.pnl.abs_position() >= self.venue_config.min_order_size \
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
            if self.engine.pnl.abs_position() < self.venue_config.min_order_size:
                self.enter_market()
            else:
                self.exit_market()

    # def quote_changed(self, side):
    #     self.on_tick()

    def on_md(self):
        if time.time() - self.last_updated_time >= self.config.refresh_timout:
            self.on_tick()
            self.last_updated_time = time.time()

    def on_exec(self, details):
        self.on_tick()

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.GAP:
            for side in Side.sides:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
