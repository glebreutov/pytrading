from decimal import Decimal

from exit_strategy import remove_exit_price_strategy
from posmath.side import Side
from instant_sumulator import simulator_env
from mmparams import MMParams
from orders import Ack
from posmath.position import Position
from printout import print_book_and_orders


def exit_price_test_func(book, pandl, broker):
    config = MMParams({
        "min_levels": "5",
        "liq_behind_exit": "0.02",
        "liq_behind_entry": {"BID": "0.41", "ASK": "0.41"},
        "order_sizes": {"BID": "0.07", "ASK": "0.07"},
        "min_profit": "0.01",
        "min_order_size": "0.01",
        "buried_volume": "1",
        "taker_exit_profit": "0.1",
        "price_tolerance": "0.0005"
    })
    start_position = Position(pandl.position(), pandl.balance())
    print("before " + str(start_position))
    exit_order = remove_exit_price_strategy(book, start_position, config)
    pandl.execution(exit_order.side(), exit_order.abs_position(), exit_order.price())
    broker.request(0, exit_order.side(), exit_order.price(), exit_order.abs_position())
    keys = broker.om.by_oid.keys()
    tmp = ''
    for x in keys:
        tmp = x

    broker.om.on_ack(Ack(tmp, 1, start_position.abs_position(), start_position.abs_position()))
    print_book_and_orders(book, broker)
    print("after " + str(exit_order))
    assert pandl.closed_pnl > 0
    return exit_order


def test_exit_price_strategy():
    # remove
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('900'), side=Side.BID)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('989')
    assert eo.side() == Side.ASK
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0
    #remove
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('900'), side=Side.BID)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('989')
    assert eo.side() == Side.ASK
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('1100'), side=Side.ASK)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('1011')
    assert eo.side() == Side.BID
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0
    #quote
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('1010'), side=Side.BID)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('1011')
    assert eo.side() == Side.ASK
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('990'), side=Side.ASK)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('989')
    assert eo.side() == Side.BID
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0
    #min profit
    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('1013'), side=Side.BID)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('1013.1427')
    assert eo.side() == Side.ASK
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0

    prior_pos = Position(pos=Decimal('0.07'), price=Decimal('900'), side=Side.ASK)
    eo = simulator_env(exit_price_test_func, prior_pos)
    assert eo.price() == Decimal('899.8572')
    assert eo.side() == Side.BID
    pos = prior_pos + eo
    print("reminder " + str(pos))
    assert pos.balance > 0

test_exit_price_strategy()