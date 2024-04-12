import asyncio
import socket

from paho.mqtt import publish

import asyncio
import socket
from paho.mqtt import publish

import asyncio
import socket
from paho.mqtt import publish

async def async_publish_single(host, topic, message, logger, timeout=60, max_retries=5):
    loop = asyncio.get_running_loop()

    def publish_message():
        published = False
        try:
            publish.single(topic, payload=message, hostname=host, qos=1)
        except asyncio.TimeoutError:
            logger.warning(f"Publishing timed out on attempt {attempt + 1}. Retrying...")
        except socket.gaierror as e:
            logger.warning(f"Attempt {attempt + 1}: Network error - {e}. Retrying...")
        published = True
        return published

    for attempt in range(max_retries):
        published = await asyncio.wait_for(
            loop.run_in_executor(None, publish_message),
            timeout=timeout
        )
        if published:
            logger.debug("Message published successfully.")
            return  # Exit the function if publish is successful


        # Wait before retrying, unless this was the last attempt
        if attempt < max_retries - 1:
            await asyncio.sleep(1)  # Wait before retrying

    # If the function hasn't returned by this point, all retries have failed
    logger.error(f"All {max_retries} attempts to publish the message have failed.")





# Example usage
# async def main():
#     host = "test.mosquitto.org"
#     topic = "test/topic"
#     message = "Hello, MQTT!"
#     timeout = 5  # seconds
#     await async_publish_single(host, topic, message, timeout)

# if __name__ == "__main__":
#     asyncio.run(main())
