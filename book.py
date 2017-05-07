from functools import reduce

from mm.event_hub import ImportantEvent
from posmath.side import Side


class BipolarContainer:
    def __init__(self, bid=None, ask=None):
        self.container = {Side.BID: bid, Side.ASK: ask}

    def bid(self):
        return self.container[Side.BID]

    def ask(self):
        return self.container[Side.ASK]

    def side(self, side):
        return self.container[side]

    def set_side(self, side, item):
        self.container[side] = item

    def __str__(self):
        return str(self.container)


class Level:
    def __init__(self, side, price, size):
        Side.check_fail(side)
        self.side = side
        self.price = price
        self.size = size
        self.next_level = None

    def before(self, level):
        if level.side != self.side:
            raise RuntimeError

        if self.price == level.price:
            raise RuntimeError

        return (self.price - level.price) / abs(self.price - level.price) == Side.sign(self.side)

    def append(self, level):
        if level.before(self):
            raise RuntimeError

        if self.next_level is None:
            self.next_level = level
        elif level.before(self.next_level):
            level.append(self.next_level)
            self.next_level = level
        else:
            self.next_level.append(level)

    def __iter__(self):
        def level_iter():
            tmp = self
            while tmp is not None:
                yield tmp
                tmp = tmp.next_level
            raise StopIteration

        return level_iter()

    def __str__(self):
        return reduce(lambda acc, x: acc + str(x) + '\t', [self.side, "{:>10.8}".format(self.price), "{:>10.8}".format(self.size)], '')

    def print_side(self, acc):

        if self.side == Side.BID:
            if self.next_level is None:
                acc.append(self)
            else:
                self.next_level.print_side(acc)
                acc.append(self)
        else:
            acc.append(self)
            if self.next_level is not None:
                self.next_level.print_side(acc)

    def volume(self):
        if self.next_level is None:
            return self.size
        else:
            return self.size + self.next_level.volume()

    def levels(self):
        if self.next_level is None:
            return 1
        else:
            return 1+self.next_level.levels()


class Book:
    def __init__(self):
        self.book = BipolarContainer()
        self.quote_subscribers = []

    def quote(self, side):
        return self.book.side(side)

    def increment_level(self, side, price, size):
        def find_level(q):
            if q is None:
                return None
            elif q.price == price:
                return q
            elif q.next_level is None:
                return None
            else:
                return find_level(q.next_level)

        level = find_level(self.quote(side))
        if size < 0.00000001:
            self.delete_level(level)
        elif level is None:
            self.add_level(side, price, size)
        else:
            level.size = size

    def quote_changed(self, side):
        if self.is_valid():
            [x.quote_changed(self.quote(side)) for x in self.quote_subscribers]

    def delete_level(self, level):
        def find_parent(find, source):
            if source.next_level is None:
                return None
            elif source.next_level == find:
                return source
            else:
                return find_parent(find, source.next_level)

        if level is None:
            return

        side = level.side
        quote = self.quote(side)
        if quote == level:
            self.book.set_side(side, level.next_level)
            self.quote_changed(side)
        else:
            parent_level = find_parent(level, quote)
            if parent_level is None:
                raise RuntimeError
            parent_level.next_level = level.next_level
            del level

    def add_level(self, side, price, size):
        level = Level(side, price, size)
        if side not in Side.sides:
            raise RuntimeError

        quote = self.book.side(side)
        if quote is None:
            self.book.set_side(side, level)
            self.quote_changed(side)
        elif level.before(quote):
            self.book.set_side(side, level)
            level.append(quote)
            self.quote_changed(side)
        else:
            quote.append(level)

    def __str__(self):
        acc = []
        if self.quote(Side.BID) is not None:
            self.quote(Side.BID).print_side(acc)
        acc.append('---------')
        if self.quote(Side.ASK) is not None:
            self.quote(Side.ASK).print_side(acc)
        return reduce(lambda a, x: a + str(x) + '\n', acc, '')

    def is_valid(self):
        return self.quote(Side.BID) is not None and self.quote(Side.ASK) is not None

    def clear(self):
        self.book = BipolarContainer()

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.GAP:
            self.clear()
