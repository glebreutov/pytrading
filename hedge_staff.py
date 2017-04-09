from _pydecimal import Decimal

from book import Level
from exit_strategy import remove_exit_price_strategy
from orders import Broker
from pnl import PNL
from posmath.position import Position
from posmath.side import Side


def remove_price(quote: Level, pos):
    last_price = 0
    while pos.abs_position() != 0:
        if pos.abs_position() > quote.size:
            pos = pos.add(quote.side, quote.size, quote.price)
        else:
            pos = pos.add(quote.side, pos.abs_position(), quote.price)
        last_price = last_price
        if quote.next_level is not None:
            quote = quote.next_level
        elif pos.abs_position():
            raise RuntimeError

    return pos, last_price


def hedge_position(prior_pos, target_price, enter_price):
    x = (target_price * prior_pos.position() - prior_pos.balance) / (enter_price - target_price)
    return Position(price=enter_price, pos=x)


def hedge_runner(book, pandl: PNL, broker: Broker):
    def hedge_workflow(prior_pos: Position, target_price, enter_price):
        # define current state
        pandl.execution(prior_pos.side(), prior_pos.abs_position(), prior_pos.price())
        exit_order = remove_exit_price_strategy(book, prior_pos, None)
        #place exit order
        broker.request(0, exit_order.side(), exit_order.price(), exit_order.abs_position())
        # calc hedge order
        hedge_pos = hedge_position(prior_pos, target_price, enter_price)
        #place hedge order
        broker.request(1, hedge_pos.side(), hedge_pos.price(), hedge_pos.abs_position())
        # exec hedge order
        pandl.execution(hedge_pos.side(), hedge_pos.abs_position(), hedge_pos.price())
        # look at new exit
        exit_order = remove_exit_price_strategy(book, Position(pandl.position(), pandl.balance()), None)


def test_hedge():
    enter_price = Decimal('989')
    target_price = Decimal('-1012')
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('1020'), side=Side.BID)

    #hedge over other side
    hedge_pos = hedge_position(prior_pos, target_price, enter_price)

    print("---------------- hedge over other side")
    print("prior " + str(prior_pos))
    print("hedge " + str(hedge_pos))
    print("fin " + str(prior_pos + hedge_pos))

    #hedge over same side
    hedge_pos = hedge_position(prior_pos, target_price, Decimal('-1011'))
    print("---------------- hedge over same side")
    print("prior " + str(prior_pos))
    print("hedge " + str(hedge_pos))
    print("fin " + str(prior_pos + hedge_pos))

    #from reality
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('1131.2700'), side=Side.ASK)
    hedge_pos = hedge_position(prior_pos, Decimal('-1159.2805'), Decimal('1161.4102'))
    print("---------------- real situation")
    print("prior " + str(prior_pos))
    print("hedge " + str(hedge_pos))
    print("fin " + str(prior_pos + hedge_pos))

#test_hedge()