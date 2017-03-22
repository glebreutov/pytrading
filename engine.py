import traceback
from decimal import Decimal

import decimal

from mm.book import Book, Side
from mm.orders import Broker, OrderManager, Ack, Replaced, Cancelled, Exec
from mm.pnl import PNL
from mm.printout import print_book_and_orders


class Engine:
    def __init__(self, algo_class):
        self.order_manager = OrderManager()
        self.book = Book()
        self.pnl = PNL()
        self.book.quote_subscribers.append(self.pnl)
        self.execution = Broker(self.order_manager)
        self.algo = algo_class(self)
    
    def on_md(self, md):
        # update book
        def update_side(side, side_name):
            for price, size in md['data'][side_name]:
                self.book.increment_level(side, Decimal(str(price)), Decimal(str(size)))

        update_side(Side.BID, 'bids')
        update_side(Side.ASK, 'asks')

        if self.book.is_valid():
            try:
                print_book_and_orders(self.book, self.execution)
                print("Balance " + str(self.pnl.balance()))
                print("Position " + str(self.pnl.position()))
                print('###########')
            except Exception:
                traceback.print_exc()

            if hasattr(self.algo, 'on_md'):
                self.algo.on_md(md)

    def on_exec(self, details):
        if hasattr(self.algo, 'on_exec'):
            self.algo.on_exec(details)

    def order_event(self, event, parsed):
        ok = True
        if 'ok' in parsed and parsed['ok'] != 'ok':
            print('Order error')
            print(parsed)
            ok = False

        if event == "place-order" and ok:
            ack = Ack(parsed['oid'],
                      str(parsed['data']['id']),
                      Decimal(str(parsed['data']['pending'])),
                      Decimal(str(parsed['data']['amount'])))
            # new order ack
            self.order_manager.on_ack(ack)
        elif event == "place-order" and not ok:
            self.order_manager.remove_order(parsed['oid'])
        elif event == "cancel-replace-order" and ok:
            repl = Replaced(parsed['oid'],
                            str(parsed['data']['id']),
                            Decimal(str(parsed['data']['pending'])),
                            Decimal(str(parsed['data']['amount'])),
                            Decimal(str(parsed['data']['price'])))
            self.order_manager.on_replace(repl)

            # replaced
        elif event == "cancel-order" and ok:
            canc = Cancelled(parsed['oid'],
                             str(parsed['data']['order_id']))
            self.order_manager.on_cancel(canc)
            # cancelled
        elif event in ["cancel-replace-order", "cancel-order"] and not ok:
            if parsed['data']['error'] == 'Error: Order not found':
                self.order_manager.remove_order(parsed['oid'])
            else:
                self.execution.rm.set_cancel_all()
                print('error occures on replace cancelling orders')
        # omg what a hack
        elif event == "tx" and 'symbol2' in parsed['data']:
            tx = Exec(Decimal(str(parsed['data']['amount'])),
                      Side.parseSide(parsed['data']['type']),
                      str(parsed['data']['order']),
                      Decimal(str(parsed['data']['price'])))
            # execution!
            self.order_manager.on_execution(tx)
            self.pnl.execution(tx)
            self.on_exec(tx)