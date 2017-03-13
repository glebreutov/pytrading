import json
import uuid
from enum import Enum

from mm.book import BipolarContainer, Side


class CancelReq:
    def __init__(self, side, order_id):
        self.side = side
        self.order_id = order_id
        self.oid = str(uuid.uuid1())


class NewReq(CancelReq):
    def __init__(self, side, price, size):
        super().__init__(side, -1)
        self.price = price
        self.size = size


class ReplaceReq(NewReq):
    def __init__(self, side, order_id, price, size):
        super().__init__(side, price, size)
        self.order_id = order_id


class Order:
    def __init__(self, side, price, size):
        self.price = price
        self.side = side

        self.order_id = -1
        self.oid = str(uuid.uuid1())
        self.status = OrderStatus.NEW
        self.amount = size
        self.pending = size


class OrderStatus(Enum):
    NEW = 0
    ACK = 1
    REQ_SENT = 2
    COMPLETED = 3


class OrderManager:
    def __init__(self):
        self.by_order_id = {}
        self.by_oid = {}
        self.request_queue = []

    def on_ack(self, details):

        oid = details['oid']
        order = self.by_oid[oid]
        order.order_id = details['data']['id']

        #price = details['data']['price']
        #side  = Side.parseSide(details['data']['side'])
        order.pending = details['data']['pending']
        order.amount = details['data']['amount']
        order.status = OrderStatus.ACK
        del self.by_oid[oid]
        self.by_order_id[order.order_id] = order

    def on_replace(self, details):
        order_id = details['data']['id']
        o = self.by_order_id[order_id]
        o.price = details['data']['price']

        o.amount = details['data']['amount']
        o.pending = details['data']['amount']

        o.status = OrderStatus.ACK

    def on_cancel(self, details):
        order_id = details['data']['id']
        order = self.by_order_id[order_id]
        order.status = OrderStatus.COMPLETED
        del order

    def on_execution(self, details):
        raise NotImplemented
        pass

    def new_req(self, side, price, size):
        order = Order(side, price, size)
        self.by_oid[order.oid] = order
        self.request_queue.append(NewReq(side, price, size))
        return order

    def replace_req(self, order_id, side, price, size):
        self.request_queue.append(ReplaceReq(side, order_id, price, size))
        return self.by_order_id[order_id]

    def cancel_req(self, order_id, side):
        self.request_queue.append(CancelReq(side, order_id))
        return self.by_order_id[order_id]


class RiskManager:
    NORMAL = 1
    CANCEL_ALL = 2

    def __init__(self, broker):
        self.broker = broker
        self.status = RiskManager.NORMAL

    def set_normal(self):
        self.status = RiskManager.NORMAL

    def set_cancel_all(self):
        self.status = RiskManager.CANCEL_ALL
        self.broker.cancel_all()

    def trading_allowed(self):
        return self.status == RiskManager.NORMAL


class Broker:

    def __init__(self, om: OrderManager):
        self.om = om
        self.orders = BipolarContainer({}, {})
        self.rm = RiskManager(self)

    def request(self, tag, side, price, size):
        orders_side = self.orders.side(side)
        if not self.rm.trading_allowed():
            self.cancel_all()
            return

        def can_replace():
            return tag in orders_side and orders_side[tag].status == OrderStatus.ACK

        def can_new():
            return tag not in orders_side or orders_side[tag].status == OrderStatus.COMPLETED

        if can_replace():
            order_id = orders_side[tag].order_id
            self.om.replace_req(order_id, side, price, size)
            pass
        elif can_new():
            orders_side[tag] = self.om.new_req(side, price, size)
            pass
        else:
            print('order in transition')

    def cancel(self, tag, side):
        order = self.orders.side(side)[tag]
        if order is not None:
            self.om.cancel_req(order.order_id, order.side)

    def cancel_all(self):

        def cancel_side(side):
            for tag in self.orders.side(side).keys():
                self.cancel(tag, side)

        cancel_side(Side.BID)
        cancel_side(Side.ASK)



