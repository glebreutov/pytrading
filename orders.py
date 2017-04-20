import json
import uuid
from decimal import Decimal
from enum import Enum

from mm.event_hub import EventHub, ImportantEvent
from mm.book import BipolarContainer
from posmath.position import Position
from posmath.side import Side


class CancelReq:
    def __init__(self, side, order_id):
        self.side = side
        self.order_id = order_id
        self.oid = str(uuid.uuid1())


class NewReq(CancelReq):
    def __init__(self, side, price: Decimal, size):
        super().__init__(side, -1)
        self.price = Decimal(price)
        self.size = Decimal(size)


class ReplaceReq(NewReq):
    def __init__(self, side, order_id, price: Decimal, size):
        super().__init__(side, price, size)
        self.order_id = order_id


class Exec:
    def __init__(self, remains, order_id, oid=None):
        self.oid = oid
        self.order_id = order_id
        self.remains = remains
        self.fee = Decimal('0')
        self.side = Side.NONE
        self.delta = 0
        self.price = 0


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


class ErrorRequest:
    ORDER_NOT_FOUND = 0
    RATE_LIMIT = 1
    INSUFICIENT_FUNDS = 2
    INVALID_AMOUNT = 3
    UNEXPECTED_ERROR = 4

    def __init__(self, oid, descr, error_class):
        self.descr = descr
        self.oid = oid
        self.error_class = error_class


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


class UnknownOid(Exception):
    pass


class UnknownOrderId(Exception):
    pass


class ExecHasNoEffect(Exception):
    pass


class NegativeAmountAfterExec(Exception):
    pass


class UnknownExec(Exception):
    pass


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
        if ack.oid not in self.by_oid.keys():
            raise UnknownOid
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
        if rep.oid not in self.by_oid.keys():
            raise UnknownOid

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
        if canc.order_id not in self.by_order_id.keys():
            raise UnknownOrderId
        order = self.by_order_id[canc.order_id]
        order.status = OrderStatus.COMPLETED
        del self.by_order_id[canc.order_id]

    def on_execution(self, tx: Exec):
        def update_order(ordr):
            delta = Decimal(ordr.amount) - abs(tx.remains)
            ordr.amount = abs(tx.remains)
            tx.side = ordr.side
            tx.price = ordr.price
            tx.delta = delta
            if ordr.amount <= 0:
                ordr.status = OrderStatus.COMPLETED
            if ordr.amount < 0:
                raise NegativeAmountAfterExec

        if tx.order_id in self.by_order_id.keys():
            order = self.by_order_id[tx.order_id]
            update_order(order)
            if order.amount <= 0:
                del self.by_order_id[tx.order_id]
        elif tx.oid is not None and tx.oid in self.by_oid.keys():
            order = self.by_oid[tx.oid]
            update_order(order)
            if order.amount <= 0:
                del self.by_oid[tx.oid]
        else:
            raise UnknownExec

    def remove_request(self, ev):
        if ev.oid not in self.by_oid:
            print("remove_request: no order for oid " + str(ev.oid))
            return
        order = self.by_oid[ev.oid]
        if order.status == OrderStatus.NEW:
            order.status = OrderStatus.COMPLETED
        elif order.status == OrderStatus.REQ_SENT:
            order.status = OrderStatus.ACK
        del self.by_oid[ev.oid]

    def remove_order(self, ev):
        if ev.oid not in self.by_oid:
            print("remove_order: no order for oid " + str(ev.oid))
            return
        order = self.by_oid[ev.oid]
        order.status = OrderStatus.COMPLETED
        if order.order_id in self.by_order_id:
            del self.by_order_id[order.order_id]

    def important_event(self, ev: ImportantEvent):
        if ev.event_name == ImportantEvent.RECONNECT:
            for oid, order in self.by_oid.items():
                if order.status == OrderStatus.REQ_SENT:
                    order.status = OrderStatus.ACK

    def market_event(self, ev):
        type_ev = type(ev)
        if type_ev == Ack:
            self.on_ack(ev)
        elif type_ev == Replaced:
            self.on_replace(ev)
        elif type_ev == Cancelled:
            self.on_cancel(ev)
        elif type_ev == Exec:
            self.on_execution(ev)
        elif type_ev == ErrorRequest:
            if ev.error_class == ErrorRequest.ORDER_NOT_FOUND:
                self.remove_order(ev)
            else:
                self.remove_request(ev)


class Broker:
    def __init__(self, om: OrderManager):
        self.om = om
        self.orders = BipolarContainer({}, {})

    def request(self, tag, side, price, size):
        orders_side = self.orders.side(side)

        def can_replace():
            return tag in orders_side and orders_side[tag].status == OrderStatus.ACK \
                   and (price != orders_side[tag].price or size != orders_side[tag].amount)

        def can_new():
            return tag not in orders_side or orders_side[tag].status == OrderStatus.COMPLETED

        if size == 0:
            print('zero size')
        elif can_replace():
            self.om.replace_req(orders_side[tag].order_id, side, price, size)
        elif can_new():
            orders_side[tag] = self.om.new_req(side, price, size)
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

    def order(self, tag, side):
        if tag in self.orders.side(side):
            return self.orders.side(side)[tag]
        return None


class RiskManager:
    NORMAL = "NORMAL"
    CANCEL_ALL = "CANCEL_ALL"
    EXIT_ONLY = "EXIT_ONLY"

    def __init__(self, broker: Broker, event_hub: EventHub):
        self.event_hub = event_hub
        self.broker = broker
        self.status = RiskManager.CANCEL_ALL

    def set_normal(self):
        self.status = RiskManager.NORMAL
        self.event_hub.rm_event(self.status)

    def set_cancel_all(self):
        self.status = RiskManager.CANCEL_ALL
        self.event_hub.rm_event(self.status)
        self.broker.cancel_all()

    def trading_allowed(self):
        return self.status == RiskManager.NORMAL

    def set_exit_only(self):
        self.status = RiskManager.EXIT_ONLY
        self.event_hub.rm_event(self.status)

    def exit_only(self):
        return self.status == RiskManager.EXIT_ONLY
