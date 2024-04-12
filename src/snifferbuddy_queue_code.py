import asyncio
from pydantic_models import SnifferBuddyModel

class SnifferBuddyQueue:
    _queue = asyncio.Queue()  # Define a class-level queue

    @classmethod
    async def put(cls, snifferbuddy_reading: SnifferBuddyModel) -> None:
        """
        Asynchronously put a SnifferBuddyModel into the queue.
        """
        await cls._queue.put(snifferbuddy_reading)

    @classmethod
    async def get(cls) -> SnifferBuddyModel:
        """
        Asynchronously get a SnifferBuddyModel from the queue.
        """
        return await cls._queue.get()

    @classmethod
    def q_size(cls) -> int:
        """
        Return the approximate size of the queue.
        """
        return cls._queue.qsize()

# Usage example:
# asyncio.run(SnifferBuddyQueue.put(SnifferBuddyModel(...)))
# model = asyncio.run(SnifferBuddyQueue.get())
