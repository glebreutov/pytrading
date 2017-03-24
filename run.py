import asyncio
import datetime
import json

import logging

import atexit
import websockets
import time
from mm.cex_serialization import auth_request, subscribe_msg, serialize_request, open_orders
from mm.client_serialization import serialize_book, serialize_orders, serialize_pnl, serialize_execs
from mm.engine import Engine
from mm.marketmaker import Marketmaker
from mm.test_algo import TestReplace, TestCancel, TestExec


class Config:
    url = None
    key = None
    secret = None


def logname():
    return 'logs/orders_'+str(time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime()))+'.log'


with open('config_prod.json', 'r') as f:
    load = json.load(f)
    Config.url = load['url']
    Config.key = load['key']
    Config.secret = load['secret']

logging.basicConfig(filename=logname(),level=logging.INFO)
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
    elif event in ["place-order", "cancel-replace-order", "cancel-order", "tx", "order"]:
        logging.info("{\"in\":" + data + "}")
        engine.order_event(event, parsed)
    elif event == 'open-orders':
        print('!open orders ' + str(len(parsed['data'])))
    else:
        logging.info("{\"in\":" + data + "}")
        print(parsed)

    q = engine.order_manager.request_queue
    req_count = len(q)
    while len(q) > 0:
        req = engine.order_manager.request_queue.pop()
        sreq = serialize_request(req)
        logging.info("{\"out\":" + sreq + "}")
        await websocket.send(sreq)
        print(sreq)

    # if req_count > 0:
    #     await websocket.send(open_orders())


def consumer(msg):
    print("new RM status" + msg)
    new_status = json.loads(msg)['new_status']
    if new_status == 'CANCELL_ALL':
        engine.execution.rm.set_cancel_all()
    elif new_status == 'NORMAL':
        engine.execution.rm.set_normal()
    else:
        print("unknown RM status" + msg)


async def sender():
    await asyncio.sleep(1)
    return [serialize_book(engine.book), serialize_orders(engine.order_manager),
            serialize_pnl(engine.pnl), serialize_execs(engine.execution_sink)]


async def handler(websocket, path):
    while True:
        listener_task = asyncio.ensure_future(websocket.recv())
        producer_task = asyncio.ensure_future(sender())

        done, pending = await asyncio.wait(
            [listener_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED)

        if listener_task in done:
            message = listener_task.result()
            consumer(message)
        else:
            listener_task.cancel()

        if producer_task in done:
            messages = producer_task.result()
            for message in messages:
                await websocket.send(message)
        else:
            producer_task.cancel()


start_server = websockets.serve(handler, 'localhost', 5678)


loop = asyncio.get_event_loop()

# {'e': 'tx', 'data': {'d': 'user:up104309133:a:BTC', 'c': 'order:3757803898:a:BTC', 'a': '0.01000000', 'ds': '0.04312206', 'cs': '0.01000000', 'user': 'up104309133', 'symbol': 'BTC', 'order': 3757803898, 'amount': '-0.01000000', 'type': 'sell', 'time': '2017-03-14T11:36:47.149Z', 'balance': '0.04312206', 'id': '3757803899'}}


loop.run_until_complete(asyncio.gather(
    start_server,
    hello(),
))
loop.run_forever()


