import json

from mm.client import ClientEventHandler
from mm.book import Book, BipolarContainer
from posmath.side import Side
from mm.orders import OrderManager, OrderStatus
from mm.pnl import PNL


def serialize_book(book: Book):
    c = BipolarContainer([], [])

    def serialize_side(side):
        quote = book.quote(side)
        while quote is not None:
            c.side(side).append([str(quote.price), str(quote.size)])
            quote = quote.next_level
    serialize_side(Side.BID)
    serialize_side(Side.ASK)
    return json.dumps({"e": "book", "details": c.container})


def serialize_orders(om: OrderManager):
    order_dump = [[str(x.price), str(x.pending), str(x.side)] for x in om.by_order_id.values()
                  if x.status != OrderStatus.COMPLETED]
    return json.dumps({"e": "orders", "details": order_dump})


def serialize_pnl(pnl: PNL):
    return json.dumps({"e": "pnl", "details": {'position': str(pnl.position()),
                       'balance': str(pnl.balance()),
                       'zero exit price': str(pnl.position_zero_price()),
                       'closed P&L': str(pnl.closed_pnl),
                       'open P&L': str(pnl.open_pnl()),
                       'nbbo P&L': str(pnl.nbbo_pnl()),
                       'take P&L': str(pnl.take_pnl()),
                       'method': str(pnl.exit_method())
                                               }})


def serialize_execs(execs):
    serialized = json.dumps({"e": "exec", "details": execs})
    execs.clear()
    return serialized


def serialize_important_events(ev_handler: ClientEventHandler):
    data = ev_handler.event_stack
    dumps = json.dumps({"e": "important_events", "details": data})
    ev_handler.event_stack.clear()
    return dumps
