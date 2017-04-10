from decimal import Decimal

from exit_strategy import stop_loss_exit_strategy
from instant_sumulator import simulator_env
from mmparams import MMParams
from orders import Ack
from posmath.position import Position
from posmath.side import Side
from printout import print_book_and_orders


def stop_loss_test_case(book, pandl, broker):
    def test_case(pos):
        config = MMParams({
            "min_levels": "5",
            "liq_behind_exit": "0.02",
            "liq_behind_entry": {"BID": "0.41", "ASK": "0.41"},
            "order_sizes": {"BID": "0.07", "ASK": "0.07"},
            "min_profit": "0.01",
            "min_order_size": "0.01",
            "buried_volume": "0.03",
            "taker_exit_profit": "0.1",
            "price_tolerance": "0.0005"
        })
        return stop_loss_exit_strategy(book, pos, config)

    position = Position(pos=pandl.position(), balance=pandl.balance())
    exit_order, method = test_case(position)
    print(method)
    broker.request(0, exit_order.side(), exit_order.price(), exit_order.abs_position())
    keys = broker.om.by_oid.keys()
    tmp = ''
    for x in keys:
        tmp = x

    broker.om.on_ack(Ack(tmp, 1, exit_order.abs_position(), exit_order.abs_position()))

    print_book_and_orders(book, broker)
    pandl.execution(exit_order.side(), exit_order.abs_position(), abs(exit_order.price()))
    print("exit order " + str(exit_order))
    print("pnl " + str(position + exit_order))


eo = simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("2000"), side=Side.BID))

simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("1011"), side=Side.BID))
simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("500"), side=Side.BID))
