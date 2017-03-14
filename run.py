import asyncio
import datetime
import json

import websockets

from mm.cex_serialization import auth_request, subscribe_msg, serialize_request
from mm.client_serialization import serialize_book, serialize_orders
from mm.engine import Engine
from mm.marketmaker import Marketmaker


class Config:
    url = None
    key = None
    secret = None

with open('config.json', 'r') as f:
    load = json.load(f)
    Config.url = load['url']
    Config.key = load['key']
    Config.secret = load['secret']

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
            await tick(websocket, data)


async def tick(websocket, data):
    parsed = json.loads(data)

    event = parsed['e']
    if event == 'md_update':
        engine.on_md(parsed)
    elif event == 'ping':
        await websocket.send(json.dumps({'e': 'pong'}))
    elif event in ["place-order", "cancel-replace-order", "cancel-order", "tx"]:
        print(parsed)
        engine.order_event(event, parsed)

    q = engine.order_manager.request_queue
    while len(q) > 0:
        req = engine.order_manager.request_queue.pop()
        sreq = serialize_request(req)
        await websocket.send(sreq)
        print(sreq)


async def serve_client(websocket, path):
    while True:
        await websocket.send(serialize_book(engine.book))
        await websocket.send(serialize_orders(engine.order_manager))

        # parsed = json.loads(data)
        # if 'e' in parsed and parsed['e'] == 'rm' and 'new_status' in parsed:
        #     if parsed['new_status'] == 'NORMAL':
        #         engine.execution.rm.set_normal()
        #     elif parsed['new_status'] == 'CANCELALL':
        #         engine.execution.rm.set_cancel_all()
        #     else:
        #         print('wrong RM status')

        await asyncio.sleep(1)

start_server = websockets.serve(serve_client, '10.115.66.134', 5678)


loop = asyncio.get_event_loop()

# {'e': 'tx', 'data': {'d': 'user:up104309133:a:BTC', 'c': 'order:3757803898:a:BTC', 'a': '0.01000000', 'ds': '0.04312206', 'cs': '0.01000000', 'user': 'up104309133', 'symbol': 'BTC', 'order': 3757803898, 'amount': '-0.01000000', 'type': 'sell', 'time': '2017-03-14T11:36:47.149Z', 'balance': '0.04312206', 'id': '3757803899'}}


loop.run_until_complete(asyncio.gather(
    start_server,
    hello(),
))
loop.run_forever()


