import asyncio
import datetime
import hashlib
import hmac
import json

import websockets

from mm.book import Book, Side
from mm.engine import Engine
from mm.marketmaker import Marketmaker


class Config:
    url = 'wss://ws.cex.io/ws/'
    key = 'IeUhsOax31Gmt3OYfFAIFHEuJo'
    secret = 'QmiVM7rdIcVkD2yxJUlBFe1yQU'


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

engine = Engine(Marketmaker)
async def hello():
    async with websockets.connect(Config.url) as websocket:
        greeting = await websocket.recv()

        print(greeting)

        req = auth_request(Config.key, Config.secret)
        await websocket.send(req)
        print("> {}".format(req))

        greeting = await websocket.recv()
        print(greeting)

        await websocket.send(subscribe_msg())

        while True:
            data = await websocket.recv()
            if data is None:
                continue

            parsed = json.loads(data)

            event = parsed['e']
            if event == 'md_update':
                engine.on_md(parsed)
            elif event == 'ping':
                await websocket.send(json.dumps({'e': 'pong'}))
            elif event == "place-order":
                # new order ack
                engine.order_event(event, parsed)
            elif event == "cancel-replace-order":
                engine.order_event(event, parsed)
                #replaced
            elif event == "cancel-order":
                engine.order_event(event, parsed)
                # cancelled
            elif event == "tx":
                engine.order_event(event, parsed)
                # execution!
                engine.on_exec(parsed)




asyncio.get_event_loop().run_until_complete(hello())
