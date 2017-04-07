import random

from book import Book
from posmath.side import Side

from book import Level


def quotes(theo):
    return theo-random.randrange(1, 10), theo + random.randrange(1, 10)

book = Book()
theo = 1000
book_levels = 5

def update_side(new_quote, side):
    level = Level(side, new_quote, 0)
    while book.quote(side) is not None and level.price != book.quote(side).price and level.before(book.quote(side)):
        book.delete_level(book.quote(side))

    for x in range(book_levels):
        book.increment_level(side, new_quote-Side.sign(side)*x, 1)



for x in range(10):
    buy, sell = quotes(theo)
    update_side(buy, Side.BID)
    update_side(sell, Side.ASK)
    print book
    print '#######'
    if book.quote(Side.BID).price >= book.quote(Side.ASK).price:
        raise RuntimeError
