import socketio
import asyncio
sio = socketio.AsyncClient()
@sio.event
async def connect():
    print("I'm connected!")

@sio.event
async def connect_error(data):
    print("The connection failed!")

@sio.event
async def disconnect():
    print("I'm disconnected!")
    # await sio.connect('http://192.168.1.197:8000')
@sio.on('/calib')
async def on_message(data):
    print('calib',data)

async def start():
    await sio.connect('http://192.168.1.197:8000')
    await sio.wait()
    # print('con')
asyncio.run(start())