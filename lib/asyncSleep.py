import asyncio 
async def sleep(time):
    await asyncio.sleep(time)
def delay(t):
    asyncio.run(sleep(t))