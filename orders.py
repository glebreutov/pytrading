import json
import uuid
from _decimal import Decimal
from enum import Enum

from mm.book import BipolarContainer, Side


class CancelReq:
    def __init__(self, side, order_id):
        self.side = side
        self.order_id = order_id
        self.oid = str(uuid.uuid1())


class NewReq(CancelReq):
    def __init__(self, side, price: Decimal, size):
        super().__init__(side, -1)
        self.price = price
        self.size = size


class ReplaceReq(NewReq):
    def __init__(self, side, order_id, price: Decimal, size):
        super().__init__(side, price, size)
        self.order_id = order_id


class Exec:
    def __init__(self, amount, side, order_id, price: Decimal):
        self.order_id = order_id
        self.side = side
        self.amount = amount
        self.price = price


class Ack:
    def __init__(self, oid, order_id, pending, amount):
        self.oid = oid
        self.order_id = order_id
        self.pending = pending
        self.amount = amount


class Replaced(Ack):
    def __init__(self, oid, order_id, pending, amount, price):
        super().__init__(oid, order_id, pending, amount)
        self.price = Decimal(str(price))


class Cancelled(Ack):
    def __init__(self, oid, order_id):
        super().__init__(oid, order_id, 0, 0)


class Order:
    def __init__(self, side, price: Decimal, size):
        self.price = price
        self.side = side

        self.order_id = -1
        self.oid = str(uuid.uuid1())
        self.status = OrderStatus.NEW
        self.amount = size


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

    def new_req(self, side, price, size):
        req = NewReq(side, price, size)
        order = Order(side, price, size)
        self.by_oid[req.oid] = order
        self.request_queue.append(req)
        return order

    def on_ack(self, ack: Ack):
        order = self.by_oid[ack.oid]
        order.order_id = ack.order_id
        order.pending = ack.pending
        order.amount = ack.amount
        order.status = OrderStatus.ACK
        self.by_order_id[order.order_id] = order
        del self.by_oid[ack.oid]

    def replace_req(self, order_id, side, price, size):
        replace_req = ReplaceReq(side, order_id, price, size)
        if order_id not in self.by_order_id:
            raise RuntimeError

        if replace_req.oid in self.by_oid:
            raise RuntimeError

        order = self.by_order_id[order_id]
        if order.price == price and order.pending == size:
            return

        self.by_oid[replace_req.oid] = order
        order.status = OrderStatus.REQ_SENT
        self.request_queue.append(replace_req)
        return order

    def on_replace(self, rep: Replaced):
        # if rep.order_id not in self.by_order_id:
        #     print('error, unknown order replacement'+str(rep))
        #     return

        o = self.by_oid[rep.oid]
        if o.order_id != rep.order_id:
            del self.by_order_id[o.order_id]
            o.order_id = rep.order_id
            self.by_order_id[o.order_id] = o

        o.price = rep.price
        o.amount = rep.pending
        o.pending = rep.amount
        o.status = OrderStatus.ACK
        del self.by_oid[rep.oid]

    def cancel_req(self, order_id, side):
        self.request_queue.append(CancelReq(side, order_id))
        return self.by_order_id[order_id]

    def on_cancel(self, canc: Cancelled):

        order = self.by_order_id[canc.order_id]
        order.status = OrderStatus.COMPLETED
        del self.by_order_id[canc.order_id]

    def on_execution(self, tx: Exec):
        order = self.by_order_id[tx.order_id]
        delta = order.amount - abs(tx.amount)
        order.amount = abs(tx.amount)

        if order.amount <= 0:
            order.status = OrderStatus.COMPLETED
            del self.by_order_id[tx.order_id]
        if order.amount < 0:
            print('error order amount less than zero')

        return order.side, delta, order.price

    def remove_order(self, oid):
        order = self.by_oid[oid]
        order.status = OrderStatus.COMPLETED
        if order.order_id in self.by_order_id:
            del self.by_order_id[order.order_id]


class RiskManager:
    NORMAL = 1
    CANCEL_ALL = 2
    EXIT_ONLY = 3

    def __init__(self, broker):
        self.broker = broker
        self.status = RiskManager.CANCEL_ALL

    def set_normal(self):
        self.status = RiskManager.NORMAL

    def set_cancel_all(self):
        self.status = RiskManager.CANCEL_ALL
        self.broker.cancel_all()

    def trading_allowed(self):
        return self.status == RiskManager.NORMAL

    def set_exit_only(self):
        self.status = RiskManager.EXIT_ONLY

    def exit_only(self):
        return self.status == RiskManager.EXIT_ONLY


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
            return tag in orders_side and orders_side[tag].status == OrderStatus.ACK \
                   and (price != orders_side[tag].price or size != orders_side[tag].amount)

        def can_new():
            return tag not in orders_side or orders_side[tag].status == OrderStatus.COMPLETED

        if can_replace():
            self.om.replace_req(orders_side[tag].order_id, side, price, size)
            pass
        elif can_new():
            orders_side[tag] = self.om.new_req(side, price, size)
            pass
        else:
            print('order in transition')

    def cancel(self, tag, side):
        if tag in self.orders.side(side):
            order = self.orders.side(side)[tag]
            if order is not None and order.status == OrderStatus.ACK:
                self.om.cancel_req(order.order_id, order.side)
                del self.orders.side(side)[tag]

    def cancel_all(self):
        def cancel_side(side, lst):
            for tag, order in lst.items():
                if order.status == OrderStatus.ACK:
                    self.om.cancel_req(order.order_id, order.side)
            lst.clear()

        cancel_side(Side.BID, self.orders.side(Side.BID))
        cancel_side(Side.ASK, self.orders.side(Side.ASK))
