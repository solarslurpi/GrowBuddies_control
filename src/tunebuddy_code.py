import asyncio
from logger_code import LoggerBase  # Assuming LoggerBase.setup_logger is correctly defined elsewhere

class SnifferBuddyQueue:
    _queue = asyncio.Queue()

    @classmethod
    async def get(cls):
        return await cls._queue.get()

    @classmethod
    async def put(cls, data):
        await cls._queue.put(data)

class SnifferBuddyProcess:
    def __init__(self, logger):
        self.logger = logger

    async def process_reading(self, max_retries=5, timeout_duration=40):
        """
        Process the data from the queue.
        """
        cnt_num = 0
        while True:
            try:
                self.logger.debug(f"Waiting for snifferbuddy reading...")
                sniffer_buddy = await asyncio.wait_for(SnifferBuddyQueue.get(), timeout=timeout_duration)
            except asyncio.TimeoutError:
                if cnt_num >= max_retries:
                    self.logger.error(f"Max count of {max_retries} reached.")
                    break
                else:
                    cnt_num += 1
                    self.logger.warning(f"Timeout of {timeout_duration} reached. Will retry {cnt_num} more times.")
                    continue

async def simulate_data_input():
    # Simulate data being put into the queue periodically
    sample_data = {"CO2": 550, "humidity": 40, "temperature": 22}
    while True:
        await asyncio.sleep(5)  # Simulate delay between data arrivals
        await SnifferBuddyQueue.put(sample_data)
        print("Simulated data has been put into the queue.")

async def main():
    logger = LoggerBase.setup_logger('test_logger')
    sniffer_buddy_process = SnifferBuddyProcess(logger)

    # Set max count of retries and timeout for the process
    max_retries = 3
    timeout_duration = 10  # seconds

    # Start the simulation of incoming data
    simulator_task = asyncio.create_task(simulate_data_input())

    # Start processing readings from the queue
    result = await sniffer_buddy_process.process_reading(max_retries, timeout_duration)
    if result is not None:
        print(f"Process completed successfully with data: {result}")
    else:
        print("Process did not complete successfully.")

    simulator_task.cancel()  # Stop the simulation
    try:
        await simulator_task
    except asyncio.CancelledError:
        print("Simulator task cancelled.")

if __name__ == "__main__":
    asyncio.run(main())
