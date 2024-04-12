from json import loads

import asyncio

from scipy.signal import find_peaks


import gym
from gym import spaces
import numpy as np



from logger_code import LoggerBase
from mqtt_code import async_publish_single
from process_udp_code import UDPProcessor
from pid_code import PID_Controller
from pydantic_models import GlobalConfig, GrowTentParams, SnifferBuddy, PIDState, MonitorParam
from q_agent_code import QLearningAgent


CONFIG_FILENAME = 'config/growbuddies_config.json'
# Observation: Error from setpoint is 500.
# Calculate Reward: Reward = -|500| = -500.
# Agent Decides: Based on the reward, the agent decides a new K value.
# Action: The environment adjusts PID parameters based on the new K value.
# Repeat: The process repeats, aiming to minimize the error (maximize reward).
class GrowTentEnv(gym.Env):
    """
    A custom Gym environment for handling sequential time chunks of sensor data coming from a grow tent,
    analyzing them, and adjusting control parameters like Kp, Ki, Kd based on the analysis.
    """
    def __init__(self, params: GrowTentParams, queue):
        super(GrowTentEnv, self).__init__()
        self.logger = LoggerBase.setup_logger('GrowTentEnv')
        self.queue = queue
        self.monitor_param = params.monitor_param
        self.tent_name = params.tent_name
        self.controller_type = params.controller_type
        self.sensor_reading_callback = params.sensor_reading_callback
        self.PID_state_callback = params.PID_state_callback
        pid_config = GlobalConfig.get_pid_config(self.tent_name, self.controller_type)
        self.hostname = pid_config.hostname
        self.snifferbuddy_incoming_port = pid_config.snifferbuddy_incoming_port
        if 0 == len(params.mqtt_power_topics):
            self.mqtt_power_topics = pid_config.mqtt_power_topics

        else:
            self.mqtt_power_topics = []
            self.logger.warning(f"There are no power topics to control turning on/off the {self.controller_type} controller.")
        # The action space (what the agent will send back to tell the environment what adjustment to make) will be a different
        # scale for co2 than vpd. This is because the agent will send back exactly how much we should adjust the parameter.
        self.action_space = spaces.Discrete(21) # 21 actions from -10 to +10.

        self.state = None  # Placeholder for the environment state
        self.pid = None
        self.received_event = asyncio.Event()  # Event to signal that a message has been received.
        self.sensor_values = [] # Used to determine when to stop Kp tuning.

    async def receive_sensor_reading_callback(self, reading) -> None:
        self.received_event.set()
        self.logger.debug(f"Received reading: {reading}")
        if self.sensor_reading_callback:
            self.logger.debug("there is a sensor reading callback...")
            await self.sensor_reading_callback(reading)  # Awaiting the async callback
        await self.handle_pid(reading)

    async def handle_pid(self, reading):
        # Transform the reading into a more accessible format
        incoming_data = loads(reading)
        snifferbuddy_data = SnifferBuddy(**incoming_data)
        # Check if the reading came from the grow tent we are interested in.
        if snifferbuddy_data.tags['location'] == self.tent_name:
            # Check if the light is off.  If it is off, don't do anything.
            print(f"light: {snifferbuddy_data.fields.light}")
            if snifferbuddy_data.fields.light == 1: # The light is on
                # Figure out what value is being controlled.
                value = None
                if self.controller_type.upper() == "CO2":
                    value = snifferbuddy_data.fields.CO2
                elif self.controller_type.upper() == "VPD":
                    value = snifferbuddy_data.fields.vpd
                if value:
                    self.sensor_values.append(value)
                # TODO: Decide if to delay by say 1/2 in the morning to let the plant wake up?

                # Send to the PID controller
                seconds_on = 0
                if value:
                    self.logger.debug(f"Sending value {value} to the {self.controller_type} PID controller")
                    seconds_on = self.pid(value)
                    if seconds_on > 0.0:
                        # Tell the power plugs to turn on but turn off after seconds_on.
                        self.logger.debug(f"Turning on the {self.controller_type} for {seconds_on} seconds.")
                        await self.turn_on_power(seconds_on, self.mqtt_power_topics)
                else:
                    self.logger.warning(f"Did not receive a value for {self.tent_name}, {self.controller_type}")

    async def turn_on_power(self,seconds_on: float, mqtt_topics: list):
        """
        Publish MQTT messages to control the power state. The method uses Tasmota's PulseTime command as a timer amount for how long to keep the power plug on.  For a quick timer, set the PulseTime between 1 and 111.  Each number represents 0.1 seconds.  If the PulseTime is set to 10, the power plug stays on for 1 second.  Longer times use setting values between 112 to 649000.  PulseTime 113 means 13 seconds: 113 - 100. PulseTime 460 = 460-100 = 360 seconds = 6 minutes.

        Args:
            power_state (int): Desired power state, either 1 (for on) or 0.
        """

        for power_topic in mqtt_topics:
            self.logger.debug(f"POWER TOPIC: {power_topic}")
            pulsetime_value = 0.0
            # Sending a 1 to the mqtt topic that the tasmota switch is listening to turns the switch on.
            await async_publish_single(self.hostname, power_topic, 1, self.logger)
            # Immediately after turning on the switch, the "PulseTime" Tasmota command is given with the number of seconds to keep the switch on.  Once this number is exceeded, the switch is turned off.
            # Tasmota's PulseTime command handles two ranges:
                ## Quick Timer Range (0.1 - 11.1 seconds): Direct mapping with each unit representing 0.1 seconds.
            # Long Timer Range (12 seconds - 6490 seconds): Here, the PulseTime value is calculated by adding 100 to the desired duration in seconds.
              # Check if duration is within the quick timer range and round to nearest tenth

            if seconds_on <= 11.1: # 111 PulseTime units or less of 0.1 seconds each
                pulsetime_value = round(seconds_on * 10)
            else:
                pulsetime_value = seconds_on + 100  # For long timer calculation
            # Create the PulseTime Topic
            # Split the topic by the '/'
            parts = power_topic.split("/")
            # Replace the last part with 'PulseTime'
            parts[-1] = "PulseTime"
            # Join the parts back together to form the new topic
            pulsetime_topic = "/".join(parts)

            await async_publish_single(self.hostname, pulsetime_topic, pulsetime_value, self.logger)
            self.logger.debug(
                f"PulseTime {pulsetime_topic} is set to {pulsetime_value} to turn off after {seconds_on} seconds."
            )

    async def receive_PID_state_callback(self, PID_state:PIDState):
        self.logger.debug(f"Received the PID state of: {PID_state.model_dump_json(indent=4)}")
        if self.PID_state_callback:
            loop = asyncio.get_running_loop()
            loop.create_task(self.PID_state_callback(PID_state))


    async def start(self):

        # We need the PID configuration info.
        pid_config = GlobalConfig.get_pid_config(self.tent_name, self.controller_type.lower())
        self.logger.debug(f"PID config: {pid_config}")
        # We need to start the PID controller.  When we start, we give it a callback to get a pid_values_dict.
        self.pid = PID_Controller(self.tent_name, self.controller_type, pid_config, self.receive_PID_state_callback)
        self.logger.debug(f"Initialized PID controller for tent {self.tent_name}, {self.controller_type}")
        # Start listening for SnifferBuddy packets.
        snifferbuddy_incoming_port = 8095
        await UDPProcessor(self.logger).init_udp_listener(self.receive_sensor_reading_callback,snifferbuddy_incoming_port)
        while True:
            await asyncio.wait_for(self.received_event.wait(), timeout=120)  # Wait for the event to be set, with a timeout
            self.received_event.clear()


    def check_if_done(self) -> bool:
        if self.monitor_param == MonitorParam.KP:
            return self._check_kp_done()
        elif self.monitor_param == MonitorParam.KI:
            return self._check_ki_done()
        elif self.monitor_param == MonitorParam.KD:
            return self._check_kd_done()
        else:
            raise ValueError(f"Unknown tuning phase: {self.monitor_param}")

    def _check_kp_done(self):
        return self._analyze_KP()


    def _check_ki_done(self):
        pass

    def _check_kd_done(self):
        pass

    def _analyze_KP(self):
        # Determine if we have enough server value readings to analyze.
        sensor_array = np.array(self.sensor_values)
        peaks, _ = find_peaks(sensor_array)
        if len(peaks) < 2: # a minimum of 2 values are needed to determine if 2 consecutive peaks are within the tolerance.
            return False

        peak_amplitudes = sensor_array[peaks]

        # Values have been analyzed.  Delete from the list
        self.sensor_values = []
        # Assess if oscillations are within tolerances for amplitude and period
        if self._are_peaks_within_tolerance(peak_amplitudes):
            return True
        first_peak_in_last_analysis = peaks[-2]  # The first peak in the last pair analyzed
        self.sensor_values = self.sensor_values[first_peak_in_last_analysis + 1:]
        return False

    def _are_peaks_within_tolerance(self,peak_amplitudes, tolerance=0.05):
        for i in range(len(peak_amplitudes) - 1):
            # Calculate the absolute difference between consecutive peaks
            amplitude_diff = abs(peak_amplitudes[i+1] - peak_amplitudes[i])
                # Use the first peak in the pair as the reference for calculating percentage difference
            if peak_amplitudes[i] > 0:  # Prevent division by zero
                percent_diff = amplitude_diff / peak_amplitudes[i]

                if percent_diff <= tolerance:
                    return True  # Found consecutive peaks within tolerance
        return False

    def apply_action(self, action):
        self.logger.debug(f"===> Gym's action: {action}")
        if self.controller_type.upper() == "CO2":
            actual_adjustment = (action - 10) * 0.1
        else:
            actual_adjustment = (action - 10) * 1
        self.logger.debug(f"Actual adjustment: {actual_adjustment}")
        if self.monitor_param == MonitorParam.KP:
            updated_Kp = self.pid.Kp + actual_adjustment
            self.pid.Kp = updated_Kp
            self.logger.debug(f"Updated Kp: {self.pid.Kp}")
            return
        if self.monitor_param == MonitorParam.KI:
            updated_Ki = self.pid.Ki + actual_adjustment
            self.pid.Ki = updated_Ki
            return
        elif self.monitor_param == MonitorParam.KD:
            updated_Kd = self.pid.Kd + actual_adjustment
            self.pid.Kd = updated_Kd
            return
        else:
            raise ValueError(f"Unknown tuning phase: {self.monitor_param}")

    def render(self):
        agent = QLearningAgent(self.logger)
