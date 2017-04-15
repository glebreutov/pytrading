import traceback
from decimal import Decimal

import decimal

import time

from mm.client import ClientEventHandler
from mm.event_hub import EventHub
from mm.book import Book
from posmath.position import Position
from posmath.side import Side
from mm.orders import Broker, OrderManager, Ack, Replaced, Cancelled, Exec, OrderStatus, ErrorRequest, UnknownOid, \
    UnknownOrderId, ExecHasNoEffect, NegativeAmountAfterExec
from mm.pnl import PNL
from mm.printout import print_book_and_orders


class Engine:
    def __init__(self, algo_class, algo_config):
        self.event_log = ClientEventHandler()
        self.order_manager = OrderManager()
        self.book = Book()
        self.pnl = PNL(algo_config['venue']['taker_comission_percent'])
        self.book.quote_subscribers.append(self.pnl)
        self.execution = Broker(self.order_manager)
        self.algo = algo_class(self, algo_config['marketmaker'])
        self.execution_sink = []
        self.snapid = -1
        self.event_hub = EventHub()
        self.event_hub.subscribe(self.book)
        self.event_hub.subscribe(self.algo)
        self.event_hub.subscribe(self.event_log)
        self.event_hub.subscribe(self.order_manager)

    def on_md(self, md):
        # update book
        def update_side(side, side_name):
            for price, size in md['data'][side_name]:
                self.book.increment_level(side, Decimal(str(price)), Decimal(str(size)))

        update_side(Side.BID, 'bids')
        update_side(Side.ASK, 'asks')

        nextsnap = int(md['data']['id'])
        if self.snapid != -1 and nextsnap - self.snapid > 1:
            print("GAP! " + str(nextsnap - self.snapid))
            self.event_hub.gap(nextsnap - self.snapid)

        self.snapid = nextsnap

        if self.book.is_valid():

            if hasattr(self.algo, 'on_md'):
                self.algo.on_md(md)

    def on_exec(self, details):
        if hasattr(self.algo, 'on_exec'):
            self.algo.on_exec(details)

    def sync_balance(self, parsed):
        print(parsed)

        #        pos = Decimal(parsed['data']['balance']['BTC']) - target_pos
        # self.pnl.
        # restore pnl
        # cancel all
        # pos = Position(pos=parsed['data']['BTC'], balance=parsed['data']['USD'])

    def order_event(self, ev):
        try:
            self.order_manager.market_event(ev)
            if type(ev) == ErrorRequest:
                self.event_hub.order_error(ev.descr)
            elif type(ev) == Exec and ev.delta > 0:
                self.pnl.execution(ev.side, ev.delta, ev.price)
                self.on_exec(ev)
                exec_time = time.strftime("%H:%M:%S", time.localtime())
                self.execution_sink.append({"time": exec_time, 'order_id': ev.order_id,
                                            'side': ev.side, 'price': str(ev.price), 'size': str(ev.delta),
                                            'timestamp': int(1000 * time.time()),
                                            'method': str(self.pnl.exit_method()),
                                            'P&L': str(self.pnl.closed_pnl)})

        except UnknownOid:
            self.event_hub.order_error('Unknown oid ' + ev.oid)
            self.execution.rm.set_cancel_all()
        except UnknownOrderId:
            self.event_hub.order_error('Unknown order id ' + ev.order_id)
            self.execution.rm.set_cancel_all()
        except ExecHasNoEffect:
            pass
        except NegativeAmountAfterExec:
            self.event_hub.order_error('NegativeAmountAfterExec')
            self.execution.rm.set_cancel_all()
