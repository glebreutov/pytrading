

from mm.book import Book, Side, print_book_and_orders
from mm.broker import DummyExecution, OrderManager
from mm.pnl import PNL


class Engine:
    def __init__(self, algo_class):
        self.order_manager = OrderManager()
        self.book = Book()
        self.pnl = PNL()
        self.book.quote_subscribers.append(self.pnl)
        self.execution = DummyExecution(self.order_manager)
        self.algo = algo_class(self)
    
    def on_md(self, md):
        # update book
        for x in md['data']['bids']:
            self.book.increment_level(Side.BID, int(1000*float(x[0])), float(x[1]))

        for x in md['data']['asks']:
            self.book.increment_level(Side.ASK, int(1000*float(x[0])), float(x[1]))

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
        pass
