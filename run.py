import asyncio
import datetime
import json

import logging
import sys
import atexit
import websockets
import time

from websockets import ConnectionClosed
from websockets import InvalidHandshake

from mm.event_hub import ImportantLogger
from mm.cex_serialization import auth_request, subscribe_msg, serialize_request, open_orders, balance, \
    deserialize_order_event, password_encode
from mm.client_serialization import serialize_book, serialize_orders, serialize_pnl, serialize_execs, \
    serialize_important_events
from mm.engine import Engine
from mm.marketmaker import Marketmaker


class Config:
    url = None
    key = None
    secret = None


def logname(dirname: str):
    return dirname+'/orders_'+str(time.strftime("%Y-%m-%d_%H%M%S", time.localtime()))+'.log'

config_file = 'config.json' if len(sys.argv) < 2 else sys.argv[1]

with open(config_file, 'r') as f:
    config = json.load(f)
    Config.url = config['venue']['url']
    Config.key = config['venue']['key']
    Config.secret = config['venue']['secret']
    logging.basicConfig(filename=logname(config['logging']['dir']), level=config['logging']['level'])

engine = Engine(Marketmaker, config)

engine.event_hub.subscribe(ImportantLogger(config['logging']['dir']))


async def reconnect():
    try:
        await hello()
    except (ConnectionClosed, InvalidHandshake):
        print("reconnecting...")
        await asyncio.sleep(1)
        engine.event_hub.reconnect()
        await reconnect()

async def hello():
    async with websockets.connect(Config.url) as websocket:
        greeting = await websocket.recv()
        print(greeting)
        req = auth_request(Config.key, Config.secret)
        await websocket.send(req)
        print("> {}".format(req))

        greeting = await websocket.recv()
        print(greeting)

        await websocket.send(subscribe_msg(config['asset']['crypto'], config['asset']['currency']))
        last_heartbeat_time = 0
        while True:
            data = await websocket.recv()
            await tick(websocket, data)
            # check socket
            if time.time() - last_heartbeat_time >= 60:
                await websocket.send(balance())
                last_heartbeat_time = time.time()

async def tick(websocket, data):
    parsed = json.loads(data)
    event = parsed['e']
    if event == 'md_update':
        engine.on_md(parsed)
    elif event == 'ping':
        await websocket.send(json.dumps({'e': 'pong'}))
    elif event in ["place-order", "cancel-replace-order", "cancel-order", "tx", "order"]:
        logging.info("{\"in\":" + data + "}")
        order_event = deserialize_order_event(event, parsed)
        if order_event is not None:
            engine.order_event(order_event)
    elif event == 'open-orders':
        print('!open orders ' + str(len(parsed['data'])))
    elif event == 'get-balance':
        engine.sync_balance(parsed)
    else:
        logging.info("{\"in\":" + data + "}")

    q = engine.order_manager.request_queue

    while len(q) > 0:
        req = engine.order_manager.request_queue.pop()
        sreq = serialize_request(req, config['asset']['crypto'], config['asset']['currency'])
        logging.info("{\"out\":" + sreq + "}")
        await websocket.send(sreq)


def consumer(msg):
    print("new RM status" + msg)
    new_status = json.loads(msg)['new_status']
    if new_status == 'CANCELL_ALL':
        engine.rm.set_cancel_all()
    elif new_status == 'NORMAL':
        engine.rm.set_normal()
    else:
        print("unknown RM status" + msg)


def client_auth(timestamp, msg):
    print("Authentication " + msg)

    auth = json.loads(msg)
    if auth["e"] == "auth":
        password = config['accounts'][auth['login']]
        return password_encode(timestamp, password) == auth['password']
    else:
        return False


async def sender():
    await asyncio.sleep(1)
    execution_count = len(engine.execution_sink)
    execs = serialize_execs(engine.execution_sink)
    if execution_count > 0:
        logging.info(execs)
    return [serialize_book(engine.book), serialize_orders(engine.order_manager),
            serialize_pnl(engine.pnl), execs, serialize_important_events(engine.event_log)]


async def handler(websocket, path):
    authenticated = False
    while not authenticated:
        timestamp = int(datetime.datetime.now().timestamp())    # UNIX timestamp in seconds
        await websocket.send(json.dumps(
            {'e': 'auth', 'timestamp': timestamp}))             # send timestamp to client.
        auth = await websocket.recv()                           # listen for login and hash of password
        authenticated = client_auth(timestamp, auth)            # check credentials

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


loop = asyncio.get_event_loop()

if config['client']['enabled']:
    start_server = websockets.serve(handler, '0.0.0.0', config['client']['port'])
    loop.run_until_complete(asyncio.gather(
        start_server,
        reconnect(),
    ))
else:
    loop.run_until_complete(asyncio.gather(
        reconnect(),
    ))
loop.run_forever()


