from mm.event_hub import ImportantEvent
from mm.book import Book
from mm.book import Side
from decimal import Decimal

from mm.book import BipolarContainer
from mm.orders import RiskManager, Broker, OrderManager
from mm.pnl import PNL
from mm.printout import print_book_and_orders


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


def test_adj_side():
    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('0.00')) == Decimal('0.07')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('0.00')) == Decimal('0.07')

    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('0.01')) == Decimal('0.06')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('0.01')) == Decimal('0.08')

    assert adjusted_size(Decimal('0.07'), Side.BID, Decimal('-0.01')) == Decimal('0.08')
    assert adjusted_size(Decimal('0.07'), Side.ASK, Decimal('-0.01')) == Decimal('0.06')


def test_exit_price_strategy():
    def test_with_params(pos, enter_price):
        pnl = PNL('0.3')
        book = Book()
        book.quote_subscribers.append(pnl)
        config = MMParams({
            "min_levels": "5",
            "liq_behind_exit": "0.02",
            "liq_behind_entry": {"BID": "0.41", "ASK": "0.41"},
            "order_sizes": {"BID": "0.07", "ASK": "0.07"},
            "min_profit": "0.01",
            "min_order_size": "0.01",

            "taker_exit_profit": "0.1"
        })
        pnl.execution(Side.side(pos), abs(pos), abs(enter_price))
        median = 1000
        for i in range(0, 5):
            book.increment_level(Side.ASK, Decimal(median + i), Decimal(i / 100))
            book.increment_level(Side.BID, Decimal(median - i), Decimal(i / 100))
            book.quote_changed(Side.BID)
            book.quote_changed(Side.ASK)

        print_book_and_orders(book, Broker(OrderManager()))
        exit_price = exit_price_strategy(book, pnl, config)
        pnl.execution(Side.opposite(pnl.position_side()), abs(pos), exit_price)

        return pnl.closed_pnl

    #take
    assert test_with_params(Decimal('0.07'), Decimal('60')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('200')) > 0
    #quote
    assert test_with_params(Decimal('0.07'), Decimal('77')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('77')) > 0
    #min profit
    assert test_with_params(Decimal('0.07'), Decimal('77')) > 0
    assert test_with_params(Decimal('-0.07'), Decimal('77')) > 0

# test_adj_side()
# test_exit_price_strategy()
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
