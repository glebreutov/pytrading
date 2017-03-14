from decimal import Decimal

import decimal

from mm.book import Book, Side, print_book_and_orders
from mm.orders import Broker, OrderManager
from mm.pnl import PNL




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
            print_book_and_orders(self.book, self.execution)
            print('###########')

            if hasattr(self.algo, 'on_md'):
                self.algo.on_md(md)

    def on_exec(self, details):
        self.pnl.on_exec(details)
        if hasattr(self.algo, 'on_exec'):
            self.algo.on_exec(details)

    def order_event(self, event, parsed):
        if parsed['ok'] != 'ok':
            print('Order error')
            print(parsed)
            return

        if event == "place-order":
            # new order ack
            self.order_manager.on_ack(parsed)
        elif event == "cancel-replace-order":
            self.order_manager.on_replace(parsed)

            # replaced
        elif event == "cancel-order":
            self.order_manager.on_cancel(parsed)
            # cancelled
        elif event == "tx":
            # execution!
            self.on_exec(parsed)
