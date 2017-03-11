from mm.book import BipolarContainer, Order


class DummyExecution:

    def __init__(self):
        self.orders = BipolarContainer({}, {})

    def request(self, tag, side, price, size):
        print("request")
        self.orders.side(side)[tag] = Order(tag, side, price, size)
        pass

    def cancel(self, tag, side):
        self.orders.side(side)[tag] = None
        pass