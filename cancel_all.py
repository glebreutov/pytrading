import json

from cex_serialization import open_orders, deserialize_side, serialize_request
from orders import CancelReq


async def cancel_all(websocket):
    await websocket.send(open_orders())
    while True:
        data = await websocket.recv()
        parsed = json.loads(data)


async def cancel_all_loop(websocket, data):
    parsed = json.loads(data)
    event = parsed['e']
    if event == 'open-orders':
        for o in parsed['data']:
            req = CancelReq(deserialize_side(o.type), o['id'])
            sreq = serialize_request(req, Config.asset.crypto, Config.asset.currency)
            logging.info("{\"out\":" + sreq + "}")
            await websocket.send(sreq)
