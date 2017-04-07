from decimal import Decimal

from mm.book import BipolarContainer
from mm.book import Book
from posmath.side import Side
from mm.event_hub import ImportantEvent
from mm.orders import RiskManager
from mm.pnl import PNL


class MMParams:
    def __init__(self, config):
        self.min_levels = Decimal(config['min_levels'])
        self.liq_behind_exit = Decimal(config['liq_behind_exit'])
        self.liq_behind_entry = BipolarContainer(Decimal(config['liq_behind_entry']['BID']),
                                                 Decimal(config['liq_behind_entry']['ASK']))
        self.order_sizes = BipolarContainer(Decimal(config['order_sizes']['BID']),
                                            Decimal(config['order_sizes']['ASK']))
        self.min_profit = Decimal(config['min_profit'])
        self.min_order_size = Decimal(config['min_order_size'])


def calc_price(quote, liq_behind):
    quote_liq = quote.size

    while quote_liq < liq_behind:
        quote = quote.next_level
        quote_liq += quote.size

    return quote.price


def should_update_price(side, current_price: Decimal, new_price: Decimal, barrier: Decimal):
    return current_price - new_price > barrier or Side.closer_to_quote(side, current_price, new_price) == new_price


def specific_margin_price(entry_price, entry_side, margin, entry_commisiion=0, exit_commision=0):
    return entry_price \
           + Side.sign(entry_side) * (margin + entry_commisiion) \
           - Side.sign(entry_side) * exit_commision


def exit_price(enter_side, enter_price, opposite_quote_price, min_profit):
    min_acceptable_price = specific_margin_price(
        enter_price,
        enter_side,
        min_profit)

    delta = opposite_quote_price - min_acceptable_price
    if delta != 0 and delta / abs(delta) != Side.sign(enter_side):
        opposite_quote_price = min_acceptable_price
    return opposite_quote_price


def tx_profit(op_quote, last_traded_price, exit_side, fee):
    return (op_quote - last_traded_price) * Side.sign(exit_side) - op_quote / 100 * fee


def adjusted_size(order_size, order_side, pos):
    pos_side = Side.side(pos)
    if pos_side == order_side:
        return order_size - abs(pos)
    else:
        return order_size + abs(pos)


def cost_of_remove_order(book: Book, side, amount, fee):
    added_vol = 0
    cost = 0
    last_price = 0
    quote = book.quote(side)
    while added_vol < amount:
        added_vol += quote.size
        cost += quote.price * quote.size
        last_price = quote.price
        if quote.next_level is not None:
            quote = quote.next_level
        elif added_vol < amount:
            return Decimal('99999999999999'), -1

    return cost + (cost / 100) * fee, last_price


def exit_price_strategy(book: Book, pnl: PNL, config: MMParams):
    pos_side = pnl.position_side()
    remove_cost, remove_price = cost_of_remove_order(book, Side.opposite(pos_side), pnl.abs_position(), pnl.fee)
    quote_price = calc_price(book.quote(pos_side), config.liq_behind_exit)
    if pnl.balance() + Side.sign(pos_side) * remove_cost > 0:
        return remove_price
    elif pnl.balance() + Side.sign(pos_side) * pnl.abs_position() * quote_price > 0:
        return quote_price
    else:
        return specific_margin_price(
            pnl.position_zero_price(),
            pnl.position_side(),
            config.min_profit)


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

    def enter_market(self):
        for side in Side.sides:
            if self.book_is_valid():
                size = adjusted_size(self.config.order_sizes.side(side), side, self.engine.pnl.position())
                self.engine.execution.request(
                    tag=Marketmaker.ENTER_TAG,
                    side=side,
                    price=calc_price(self.engine.book.quote(side), self.config.liq_behind_entry.side(side)),
                    size=str(size)
                )
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
            else:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)

    def exit_market(self):
        print("placing exit order")

        for side in Side.sides:
            self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
        if self.book_is_valid():
            exit_side = Side.opposite_side(self.engine.pnl.position())
            quote_price = calc_price(self.engine.book.quote(exit_side), self.config.liq_behind_exit)

            eprice = exit_price(self.engine.pnl.position_side(),
                                self.engine.pnl.position_zero_price(),
                                quote_price,
                                self.config.min_profit)
            if self.engine.pnl.abs_position() >= self.config.min_order_size:
                self.engine.execution.request(Marketmaker.EXIT_TAG, exit_side, eprice,
                                              str(self.engine.pnl.abs_position()))
                self.engine.pnl.update_open_pnl(eprice)

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
