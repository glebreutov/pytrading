from decimal import Decimal

from instant_simulator import gen_book
from new_approach import hedge_positon_size, bound_price_to_lower_quote, bound_pos_to_lower_quote, calc_target_price
from orders import Broker, OrderManager, Ack
from posmath.position import Position
from posmath.side import Side
from printout import print_book_and_orders


def test_hedge_order():
    position = Position(side=Side.BID, price=Decimal('1500'), pos=Decimal('0.01'))
    hedge_pos = hedge_positon_size(position, Decimal('1500') * Decimal('1.01'), Decimal('0.01'))
    print(hedge_pos)
    print(position + hedge_pos)


def test_stick_to_quote(position):

    book = gen_book()

    print(position)
    position = bound_pos_to_lower_quote(book.quote(position.side()), position, Decimal('0.0001'))
    broker = Broker(OrderManager())
    broker.request(0, position.side(), position.price(), position.abs_position())
    keys = broker.om.by_oid.keys()
    tmp = ''
    for x in keys:
        tmp = x
    broker.om.on_ack(Ack(tmp, 1, position.abs_position(), position.abs_position()))
    print_book_and_orders(book, broker)
    print("\n\n")


def test_target_price(pos: Position):
    book = gen_book()
    theo = (book.quote(Side.BID).price + book.quote(Side.ASK).price) / 2
    target_price = calc_target_price(Decimal(theo), pos, Decimal('0.01'))
    print(pos)
    print("theo " + str(theo))
    print("target " + str(target_price))
    hedge_pos = hedge_positon_size(pos, target_price, Decimal('0.01'))
    print("pos for target " + str(hedge_pos))
    print("fianl pos " + str(pos + hedge_pos))
    # print("nbbo pnl " + str(pos + hedge_pos))

    print("---------")

test_stick_to_quote(Position(pos='0.01', price='1300', side=Side.BID))
test_stick_to_quote(Position(pos='0.01', price='1297', side=Side.BID))

test_stick_to_quote(Position(pos='0.01', price='1300', side=Side.ASK))
test_stick_to_quote(Position(pos='0.01', price='1302', side=Side.ASK))


test_target_price(Position(pos='0.01', price='1300', side=Side.BID)) # good
test_target_price(Position(pos='0.01', price='1300', side=Side.BID)) # good
test_target_price(Position(pos='0.01', price='1500', side=Side.BID)) # perfect

test_target_price(Position(pos='0.01', price='1300', side=Side.ASK))
test_target_price(Position(pos='0.01', price='1500', side=Side.ASK))
test_target_price(Position(pos='0.01', price='1000', side=Side.ASK))