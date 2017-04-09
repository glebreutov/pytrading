from decimal import Decimal

from exit_strategy import stop_loss_exit_strategy
from instant_sumulator import simulator_env
from mmparams import MMParams
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
            "taker_exit_profit": "0.1"
        })
        return stop_loss_exit_strategy(book, pos, config)

    position = Position(pos=pandl.position(), balance=pandl.balance())
    exit_order = test_case(position)
    broker.request(0, exit_order.side(), exit_order.price(), exit_order.abs_position())
    print_book_and_orders(book, broker)
    pandl.execution(exit_order.side(), exit_order.abs_position(), abs(exit_order.price()))
    print("pnl " + str(position + exit_order))

simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("2000"), side=Side.BID))
simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("1011"), side=Side.BID))
simulator_env(stop_loss_test_case, Position(pos=Decimal("0.07"), price=Decimal("1000"), side=Side.BID))
