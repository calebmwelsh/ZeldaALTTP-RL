import asyncio
import websockets
import gym
import json
import threading

class StreamWrapper(gym.Wrapper):
    def __init__(self, env, ws_address="ws://localhost:8765", stream_metadata=None, upload_interval=300):
        super().__init__(env)
        self.ws_address = ws_address
        self.stream_metadata = stream_metadata or {}
        self.upload_interval = upload_interval
        self.step_counter = 0
        self.coord_list = []
        self.loop = asyncio.new_event_loop()
        self.websocket = None
        self._start_event_loop_thread()

    def _start_event_loop_thread(self):
        def run_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        self.loop_thread = threading.Thread(target=run_loop, args=(self.loop,), daemon=True)
        self.loop_thread.start()
        asyncio.run_coroutine_threadsafe(self._establish_ws_connection(), self.loop)

    def step(self, action):
        obs, reward, done, info = self.env.step(action)
        # Try to extract coordinates from info or env attributes
        coords = info.get("player_coords") if isinstance(info, dict) and "player_coords" in info else None
        if coords:
            self.coord_list.append(coords)
        self.step_counter += 1

        if self.step_counter >= self.upload_interval:
            self.stream_metadata["extra"] = f"steps: {self.step_counter}"
            data = {
                "metadata": self.stream_metadata,
                "coords": self.coord_list
            }
            asyncio.run_coroutine_threadsafe(
                self._broadcast_ws_message(json.dumps(data)),
                self.loop
            )
            self.step_counter = 0
            self.coord_list = []

        return obs, reward, done, info

    async def _broadcast_ws_message(self, message):
        if self.websocket is None:
            await self._establish_ws_connection()
        if self.websocket is not None:
            try:
                await self.websocket.send(message)
            except Exception:
                self.websocket = None

    async def _establish_ws_connection(self):
        try:
            self.websocket = await websockets.connect(self.ws_address)
        except Exception:
            self.websocket = None 