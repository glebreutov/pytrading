import datetime
import hashlib
import hmac
import json

from mm.book import Side
from mm.orders import NewReq, ReplaceReq, CancelReq


def create_signature(key, secret):  # (string key, string secret)
    timestamp = int(datetime.datetime.now().timestamp())  # UNIX timestamp in seconds
    string = "{}{}".format(timestamp, key)
    return timestamp, hmac.new(secret.encode(), string.encode(), hashlib.sha256).hexdigest()


def auth_request(key, secret):
    timestamp, signature = create_signature(key, secret)
    return json.dumps({'e': 'auth',
                       'auth': {'key': key, 'signature': signature, 'timestamp': timestamp, }, 'oid': 'auth', })


def subscribe_msg():
    return json.dumps({
        "e": "order-book-subscribe",
        "data": {
            "pair": [
                "BTC",
                "USD"
            ],
            "subscribe": True,
            "depth": 5
        },
        "oid": "1435927928274_3_order-book-subscribe"
    })


def serialize_side(side):
    return 'buy' if side == Side.BID else 'sell'


def serialize_request(req):
    if type(req) == NewReq:
        return json.dumps({
            "e": "place-order",
            "data": {
                "pair": [
                    "BTC",
                    "USD"
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
                    "BTC",
                    "USD"
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