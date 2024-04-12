import asyncio

from logger_code import LoggerBase
from process_udp_code import fill_queue
from pydantic_models import MonitorParam
from snifferbuddy_queue_code import SnifferBuddyQueue

class PIDController:
    def __init__(self, monitor_param, tent_name, controller_type, udp_port):
        self.logger = LoggerBase.setup_logger('tune_buddy')
        self.monitor = monitor_param
        self.tent_name = tent_name
        self.controller_type = controller_type
        self.udp_port = udp_port
        self.logger.debug("Finished init.")

    async def process_queue(self):
        cnt_num = 0
        timeout = 40
        max_cnt = 20
        while True:
            try:
                self.logger.debug(f"Waiting for snifferbuddy reading...")
                sniffer_buddy = await asyncio.wait_for(SnifferBuddyQueue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                if cnt_num >= max_cnt:
                    self.logger.error(f"Max count of {max_cnt} reached.")
                    break
                else:
                    cnt_num += 1
                    self.logger.warning(f"Timeout of {timeout} reached. Will retry {cnt_num} more times.")
                    continue
            self.logger.debug(f"Received snifferbuddy reading: {sniffer_buddy}")
            # TODO: Do something with the sniffer_buddy
            # TODO: Do something with the PID environment
            # TODO: Do something with the PID controller
            # TODO: Do something with the MQTT broker
            # TODO: Do something with the telegraf
    async def main_loop(self):
        queue_task = asyncio.create_task(fill_queue(self.udp_port, self.logger))
        # pid_env_task = asyncio.create_task(self.env.start())
        processor_task = asyncio.create_task(self.process_queue())
        await asyncio.gather(queue_task,  processor_task)

if __name__ == "__main__":
    controller = PIDController(monitor_param=MonitorParam.KP,
                               tent_name="tent_one",
                               controller_type="VPD",
                               udp_port=8095)
    asyncio.run(controller.main_loop())