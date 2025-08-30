import os
import asyncio
from stagehand import Stagehand

stagehand = Stagehand(
    env="LOCAL",
    headless="False"
)

async def start():
    await stagehand.init()
    print(f"Session ID: {stagehand.session_id}")

if __name__ == "__main__"

