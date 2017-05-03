# ema in a middle
# ema closer to bid
# ema closer to ask
# ema crosses bid
# ema crosses ask
from decimal import Decimal

from instant_simulator import gen_book
from order_algos import enter_ema
from orders import Broker
from posmath.side import Side
from printout import print_book_and_orders
from orders import OrderManager

book = gen_book(1300, 1, 20)
broker = Broker(OrderManager())


def place_orders(ema):
    decimal = Decimal('0.5')
    bid_price = enter_ema(book.quote(Side.BID), ema, decimal)
    ask_price = enter_ema(book.quote(Side.ASK), ema, decimal)
    broker.request(0, Side.BID, bid_price, Decimal('0.07'))
    broker.request(0, Side.ASK, ask_price, Decimal('0.07'))
    print_book_and_orders(book, broker)


place_orders(Decimal(1350))