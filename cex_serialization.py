import datetime
import hashlib
import hmac
import json

from decimal import Decimal

from posmath.side import Side
from mm.orders import NewReq, ReplaceReq, CancelReq, ErrorRequest, Exec, Ack, Replaced, Cancelled


def create_signature(key, secret):  # (string key, string secret)
    timestamp = int(datetime.datetime.now().timestamp())  # UNIX timestamp in seconds
    string = "{}{}".format(timestamp, key)
    return timestamp, hmac.new(secret.encode(), string.encode(), hashlib.sha256).hexdigest()


def auth_request(key, secret):
    timestamp, signature = create_signature(key, secret)
    return json.dumps({'e': 'auth',
                       'auth': {'key': key, 'signature': signature, 'timestamp': timestamp, }, 'oid': 'auth', })


def subscribe_msg(crypto="BTC", currency="USD"):
    return json.dumps({
        "e": "order-book-subscribe",
        "data": {
            "pair": [
                crypto,
                currency
            ],
            "subscribe": True,
            "depth": 10
        },
        "oid": "1435927928274_3_order-book-subscribe"
    })


def serialize_side(side):
    return 'buy' if side == Side.BID else 'sell'


def deserialize_side(side):
    return Side.BID if side == 'buy' else Side.ASK


def serialize_request(req, crypto="BTC", currency="USD"):
    if type(req) == NewReq:
        return json.dumps({
            "e": "place-order",
            "data": {
                "pair": [
                    crypto,
                    currency
                ],
                "amount": req.size,
                "price": str(req.price),
                "type": serialize_side(req.side)
            },
            "oid": req.oid
        })
    elif type(req) == ReplaceReq:
        return json.dumps({
            "e": "cancel-replace-order",
            "data": {
                "order_id": req.order_id,
                "pair": [
                    crypto,
                    currency
                ],
                "amount": req.size,
                "price": str(req.price),
                "type": serialize_side(req.side)
            },
            "oid": req.oid
        })
    elif type(req) == CancelReq:
        return json.dumps({
            "e": "cancel-order",
            "data": {
                "order_id": req.order_id
            },
            "oid": req.oid
        })
    else:
        raise RuntimeError


def parse_cex_error(error_descr):
    if error_descr == 'Error: Place order error: Insufficient funds.':
        return ErrorRequest.INSUFICIENT_FUNDS
    elif error_descr == 'Rate limit exceeded':
        return ErrorRequest.RATE_LIMIT
    elif error_descr == 'Error: Order not found':
        return ErrorRequest.ORDER_NOT_FOUND
    else:
        return ErrorRequest.UNEXPECTED_ERROR


def deserialize_order_event(event, parsed):
    if 'ok' in parsed and parsed['ok'] != 'ok' or 'error' in parsed['data']:
        error_descr = parsed['data']['error'].strip()
        return ErrorRequest(parsed['oid'], error_descr, parse_cex_error(error_descr))

    if "complete" in parsed['data'] and parsed['data']['complete'] is True:
        return Exec(Decimal('0'),
                    str(parsed['data']['id']), parsed['oid'])
    elif event == "place-order":
        return Ack(parsed['oid'],
                   str(parsed['data']['id']),
                   Decimal(str(parsed['data']['pending'])),
                   Decimal(str(parsed['data']['amount'])))

    elif event == "cancel-replace-order":
        return Replaced(parsed['oid'],
                        str(parsed['data']['id']),
                        Decimal(str(parsed['data']['pending'])),
                        Decimal(str(parsed['data']['amount'])),
                        Decimal(str(parsed['data']['price'])))
    elif event == "cancel-order":
        return Cancelled(parsed['oid'], str(parsed['data']['order_id']))
    elif event == "order" and "cancel" not in parsed['data']:
        return Exec(Decimal(str(parsed['data']['remains'])) / 100000000,
                    str(parsed['data']['id']))
    else:
        print("Ignored event " + str(parsed))
        return None


def open_orders(crypto="BTC", currency="USD"):
    return json.dumps({
        "e": "open-orders",
        "data": {
            "pair": [
                crypto,
                currency
            ]
        },
        "oid": "1435927928274_6_open-orders"
    })


def balance():
    return json.dumps({
        "e": "get-balance",
        "data": {},
        "oid": "1435927928274_2_get-balance"
    })


