import re, json, time
import requests
import uvicorn

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from datetime import datetime
# from sqlalchemy import create_engine
from pydantic import BaseModel
# from apscheduler.schedulers.background import BackgroundScheduler
from arq import cron

"""
Note: code layout inspired by https://github.com/cthwaite/fastapi-websocket-broadcast/blob/master/app.py
"""

### INIT
app = FastAPI()

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://10.0.0.134:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

### CLASSES
class MinerInfo(BaseModel):
    """ Miner metadata.
    """

    miner_id: str
    connected_at: float

class Stratum:
    """ Mining Stratum for Miners
    """

    def __init__(self):
        logging.info(f'New Stratum server...')
        self._miners: Dict[str, WebSocket] = {}
        self._miner_meta: Dict[str, MinerInfo] = {}

    def __len__(self) -> int:
        """ Number of Miners
        """
        return len(self._miners)

    @property
    def empty(self) -> bool:
        """ ...Hello?
        """
        return len(self._miners) == 0

    @property
    def miner_list(self) -> List[str]:
        """ List connected Miners
        """
        return list(self._miners)

    def add_miner(self, miner_id: str, websocket: WebSocket):
        """ Add a Miner websocket, keyed by corresponding worker.rig
        Raises:
            ValueError: If the `miner` already exists on server
        """
        if miner_id in self._miners:
            raise ValueError(f"Miner {miner_id} is already in the room")
        logging.info(f"Adding {miner_id}...")
        self._miners[miner_id] = websocket
        self._miner_meta[miner_id] = MinerInfo(miner_id=miner_id, connected_at=time.time())

    def remove_miner(self, miner_id: str):
        """Remove a miner from stratus
        Raises:
            ValueError: If the `miner` is not held within the room.
        """
        if miner_id not in self._miners:
            raise ValueError(f"Miner {miner_id} is not in the room")
        logging.info(f'Removing miner {miner_id} from stratum')
        del self._miners[miner_id]
        del self._miner_meta[miner_id]

    async def broadcast_message(self, msg: str):
        """Broadcast message to all miners.
        """
        for websocket in self._miners.values():
            await websocket.send_json({"type": "KEEPALIVE", "msg": msg})

### ROUTES
@app.get("/chat")
async def get():
    return HTMLResponse(html)

async def stay_awake(ctx):
    stratum: Optional[Stratum] = request.get('stratum')
    if stratum is None:
        logging.error('Global Stratum not defined...')
    else:
        await stratum.broadcast_message('hello')

@app.on_event("startup")
async def startup_event():
    class WorkerSettings:
        cron_jobs = [
            cron(stay_awake, hour={9, 12, 18}, minute=12)
        ]            

@app.on_event("shutdown")
async def shutdown_event():
    await arq.close()

@app.websocket_route("/", name="ws")
class StratumServer(WebSocketEndpoint):

    encoding: str = "text"
    session_name: str = ""
    count: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stratum: Optional[Stratum] = None
        self.miner_id: Optional[str] = None
    
    # @classmethod
    # def get_next...

    async def broadcast(self, msg):
        await self.stratum.broadcast_message(msg)

    async def on_connect(self, websocket):
        """Handle new connection

        Miners id in format: worker.rig, and added to global Stratum
        """
        await websocket.accept()
        text = await websocket.receive_text()
        try:
            if ('method' in res) and ('params' in jsn): 
                if 'id' in jsn: # if missing, it's a notification
                    isValid = True
                # if ('jsonrpc' in jsn):
                #    if jsn['jsonrpc'] == "2.0":
        except Exception as e:
            logging.error(e)            

        if text['method'] == 'hello':
            logging.info(f'Authorized {miner_id}...')
            stratum: Optional[Stratum] = self.scope.get("stratum")
            if stratum is None:
                raise RuntimeError(f'Global `Stratum` instance not available...')
            self.stratum = stratum
            self.miner_id = text['params']
            await websocket.send_json({"miner_id": self.miner_id})
            self.stratum.add_miner(self.miner_id, websocket)
        else:
            logging.debug(f'Unauthorized or malformed request...')

    async def on_disconnect(self, _websocket: WebSocket, _close_code: int):
        """Disconnect miner, removing them from the Stratum
        """
        if self.miner_id is None:
            logging.error(f'invalid miner_id')
        self.stratum.remove_miner(self.miner_id)

    async def on_receive(self, _websocket: WebSocket, msg: Any):
        """Handle incoming messages
        """
        if self.miner_id is None:
            logging.error(f'on_receive with invalid miner_id')
        if not isinstance(msg, str):
            raise ValueError(f'on_receive with invalid data: {msg}'')

        jsn = json.loads(msg)
        # is it json rpc? 2.0?
        isValid = False
        try:
            if ('method' in res) and ('params' in jsn): 
                if 'id' in jsn: # if missing, it's a notification
                    isValid = True
                # if ('jsonrpc' in jsn):
                #    if jsn['jsonrpc'] == "2.0":
        except Exception as e:
            logging.error(e)            

        # valid JSON RPC msg; handle these scenarios
        if isValid:
            prm = jsn['params']
            idv = jsn['id']

            # Example request: {“id”: 1, “method”: “mining.subscribe”, “params”: [“Node/1.0.0”]}
            # Example response: {“result”:[[[“mining.set_difficulty”,“731ec5e0649606ff”],[“mining.notify”,“731ec5e0649606ff”]],“e9695791”,4],“id”:1,“error”:null} 
            if jsn['method'] == 'mining.subscribe': 
                res = MiningSubscribe(prm, idv)
                MinintNotify(res, prm, idv) # Example request: {“id”: null, “method”: “mining.notify”, “params”: [“bf”, “4d16b6f85af6e2198f44ae2a6de67f78487ae5611b77c6c0440b921e00000000”,“01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff20020862062f503253482f04b8864e5008”,“072f736c7573682f000000000100f2052a010000001976a914d23fcdf86f7e756a64a7a9688ef9903327048ed988ac00000000”, [],“00000002”, “1c2ac4af”, “504e86b9”, false]}

            # Example request: {“id”: 1, “method”: “mining.authorize”, “params”: [“username”, “p4ssw0rd”]}
            # Example response: {“id”: 2, “result”: true, “error”: null}
            if jsn['method'] == 'mining.authorize': 
                res = MiningAuthorize(jsn['params'])
                MinintNotify(res, prm, idv) # Example request: {“id”: null, “method”: “mining.notify”, “params”: [“bf”, “4d16b6f85af6e2198f44ae2a6de67f78487ae5611b77c6c0440b921e00000000”,“01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff20020862062f503253482f04b8864e5008”,“072f736c7573682f000000000100f2052a010000001976a914d23fcdf86f7e756a64a7a9688ef9903327048ed988ac00000000”, [],“00000002”, “1c2ac4af”, “504e86b9”, false]}

            # Example request: {“id”: 1, “method”: “mining.submit”, “params”: [“username”, “4f”, “fe36a31b”, “504e86ed”, “e9695791”]}
            # Example response: {“id”: 2, “result”: true, “error”: null}
            if jsn['method'] == 'mining.submit': 
                res = MiningSubmit(jsn['params'])
                MiningSetDifficulty(res, prm, idv) # Example request: { “id”: null, “method”: “mining.set_difficulty”, “params”: [2]}
        
        # await websocket.send_text(f"Message text was: {data}")

### MAIN
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
