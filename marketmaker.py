from decimal import Decimal

import time

from mm.app_config import AppConfig, MarketmakerConfig, VenueConfig

from mm.order_algos import price_on_a_depth, enter_ema, ema_constraint
from mm.event_hub import ImportantEvent
from mm.order_algos import stop_loss_exit_strategy
from mm.orders import RiskManager, OrderStatus
from mm.new_approach import enter_hedge, bound_price_to_lower_quote, HedgeConfig
from posmath.side import Side


def should_update_price(side, current_price: Decimal, new_price: Decimal, barrier: Decimal):
    return current_price - new_price > barrier or Side.closer_to_quote(side, current_price, new_price) == new_price


class Marketmaker:
    ENTER_TAG = 0
    EXIT_TAG = 1

    def __init__(self, engine):
        self.last_updated_time = time.time()
        self.engine = engine
        self.config: HedgeConfig = self.engine.config.algo
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

    def place_pos(self, pos):
        tag = Marketmaker.ENTER_TAG
        changed = self.price_changed(Marketmaker.ENTER_TAG, pos.side(), pos.price(), pos.abs_position())
        if pos.abs_position() != 0 and changed:
            self.engine.execution.request(
                tag=tag,
                side=pos.side(),
                price=pos.price(),
                size=pos.abs_position()
            )
        elif pos.abs_position() == 0:
            self.engine.execution.cancel(tag, pos.side())

    def hedge_step(self):
        pnl = self.engine.pnl
        for side in Side.sides:
            quote = self.engine.book.quote(side)
            pos, method = enter_hedge(pnl, quote, self.config, self.venue_config)
            self.place_pos(pos)

            if side != pnl.position_side() and pnl.pos.position() != 0:
                self.engine.pnl.update_open_pnl(pos.price())
            pnl.set_order_method(side, method)

    def on_tick(self):
        risk_status = self.engine.rm.status
        if risk_status == RiskManager.CANCEL_ALL or not self.book_is_valid():
            self.engine.execution.cancel_all()
        else:
            self.hedge_step()


    def on_md(self):
        if time.time() - self.last_updated_time >= self.config.refresh_timeout:
            self.on_tick()
            self.last_updated_time = time.time()

    def on_exec(self, details):
        self.on_tick()

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.GAP:
            for side in Side.sides:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
