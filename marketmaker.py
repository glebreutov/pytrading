from mm.event_hub import ImportantEvent
from mm.book import Book
from mm.book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import RiskManager


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
        enter_side, min_profit)

    delta = opposite_quote_price - min_acceptable_price
    if delta != 0 and delta / abs(delta) != Side.sign(enter_side):
        opposite_quote_price = min_acceptable_price
    return opposite_quote_price


def tx_profit(op_quote, last_traded_price, exit_side, fee):
    return (op_quote - last_traded_price) * Side.sign(exit_side) - op_quote / 100 * fee


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
                self.engine.execution.request(
                    tag=Marketmaker.ENTER_TAG,
                    side=side,
                    price=calc_price(self.engine.book.quote(side), self.config.liq_behind_entry.side(side)),
                    size=str(self.config.order_sizes.side(side)))
                self.engine.execution.cancel(Marketmaker.EXIT_TAG, side)
            else:
                self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)

    def exit_market(self):
        print("placing exit order")

        for side in Side.sides:
            self.engine.execution.cancel(Marketmaker.ENTER_TAG, side)
        # todo: add quote is null check
        if self.book_is_valid():
            exit_side = Side.opposite_side(self.engine.pnl.position())
            quote_price = calc_price(self.engine.book.quote(exit_side), self.config.liq_behind_exit)

            eprice = exit_price(self.engine.pnl.last_traded_side(),
                                self.engine.pnl.last_traded_price(),
                                quote_price,
                                self.config.min_profit)
            if self.engine.pnl.abs_position() >= self.config.min_order_size:
                self.engine.execution.request(Marketmaker.EXIT_TAG, exit_side, eprice, str(self.engine.pnl.abs_position()))
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






        # print(exit_price(Side.BID, 100, 105))
        # print(exit_price(Side.ASK, 105, 100))
        #
        # print(exit_price(Side.BID, 100, 90))
        # print(exit_price(Side.ASK, 105, 110))

        # mm = Marketmaker(None)
        # bid_price = Decimal(1109.785)
        # print(mm.specific_margin_price(bid_price, Side.BID, Decimal('1')))
        # ask_price = 1000
        # print(mm.specific_margin_price(bid_price, Side.ASK, Decimal('0.1')))
