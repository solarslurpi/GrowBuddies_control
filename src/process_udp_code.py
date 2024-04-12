import asyncio
from pydantic import ValidationError
from pydantic_models import SnifferBuddyModel
from snifferbuddy_queue_code import SnifferBuddyQueue

class SimpleUDPServer(asyncio.DatagramProtocol):
    def __init__(self, logger):
        self.logger = logger

    def connection_made(self, transport):
        self.transport = transport
        self.logger.debug(f"UDP Server started on {transport.get_extra_info('sockname')}")

    async def datagram_received(self, data, addr):
        message = data.decode()
        self.logger.debug(f"Received UDP snifferbuddy reading: {message} from {addr}")
        try:
            sniffer_buddy = SnifferBuddyModel.model_validate_json(message)
            await SnifferBuddyQueue.put(sniffer_buddy)
            self.logger.debug("Validated snifferbuddy reading and added to processing queue.")
        except ValidationError as e:
            self.logger.error(f"Validation error for received data: {e}")
            return False
        return True

    def error_received(self, exc):
        self.logger.error('UDP error received:', exc)

    def connection_lost(self, exc):
        self.logger.debug('UDP connection closed:', exc)
        self.transport.close()

async def fill_queue(port, logger):
    loop = asyncio.get_running_loop()
    _, protocol = await loop.create_datagram_endpoint(
        lambda: SimpleUDPServer(logger),
        local_addr=('0.0.0.0', port)
    )
    return protocol
