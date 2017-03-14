from book import Side


class SidePnl:
    def __init__(self):
        self.position = 0
        self.pending = 0
        self.quote_price = 0


class PNL:
    def __init__(self):
        self.pnl = {Side.BID: SidePnl(), Side.ASK: SidePnl()}
        self.ask = self.pnl[Side.ASK]
        self.bid = self.pnl[Side.BID]

    def execution(self, details):
        self.pnl[Side.sign(details.side)].position + abs(details.size)

    def position(self):
        return self.pnl[Side.BID].position - self.pnl[Side.ASK].position

    def abs_position(self):
        return abs(self.position())

    def quote_changed(self, quote):
        self.pnl[quote.side].quote_price = quote.price

    def balance(self):
        return abs(self.position() * self.pnl[Side.opposite_side(self.position())].quote_price)

    def on_exec(self, details):
        pass
