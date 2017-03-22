import json

from mm.book import Book, BipolarContainer, Side
from mm.orders import OrderManager


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
    order_dump = []
    for x in om.by_order_id:
        order_dump.append([x.price, x.pending, x.side])

    return json.dumps({"e": "orders", "details": order_dump})