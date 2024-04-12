#############################################################################
# SPDX-FileCopyrightText: 2024 Margaret Johnson
#
# SPDX-License-Identifier: MIT
#
#############################################################################
import asyncio
from enum import Enum
import time
from typing import Any, Callable, Optional

from logger_code import LoggerBase
from pydantic_models import PidConfigModel, PIDState

class ControllerType(Enum):
    CO2 = "CO2",
    VPD = "VPD"

COMPARISON_FUNCTIONS = {
    "greater_than": lambda x, max_val: x > max_val,
    "less_than": lambda x, max_val: x < max_val,
}

def _clamp(value, limits):
    lower, upper = limits
    if value is None:
        return None
    value = abs(
        value
    )  # The direction to move might be up or down. But n seconds is always positive.
    if (upper is not None) and (value > upper):
        return upper
    elif (lower is not None) and (value < lower):
        return lower
    return value


class PID_Controller(object):
    def __init__(self, tent_name:str, controller_type:str, pid_config: PidConfigModel, callback: Optional[Callable[..., Any]] = None) -> None:
        self.logger = LoggerBase.setup_logger('PID_Control')
        self.config = pid_config
        self.tent_name = tent_name
        self.controller_type = controller_type
        self.callback = callback
        callback_name = self.callback.__name__ if self.callback and hasattr(self.callback, '__name__') else 'None'
        self.logger.debug(f"\n--------------\nConfig: {self.config}\nTent name: {self.tent_name}\nController type: {self.controller_type}\nCallback: {callback_name}")

        self._last_value = None

        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._Kp = pid_config.Kp
        self._Ki = pid_config.Ki
        self._Kd = pid_config.Kd


        self._last_time = time.monotonic()

        # For co2, getting too far about the setpoint is dangerous.
        # For vpd, getting too far below the setpoint invites pathogens and powdery mildew.
        # one needs a greater than check, the other a less than check.
        self.comparison_func=COMPARISON_FUNCTIONS[self.config.comparison_function]
        if self.config.comparison_function.lower() == "greater_than":
            self.sign = 1
        else:
            self.sign = -1

    def __call__(self, current_value:float) -> float:

        # Determine if it is time to tune.
        now = time.monotonic()
        dt = now - self._last_time if (now - self._last_time) else 1e-16
        self._last_time = now

        # d_value calculates the difference between the current reading and the last reading. It's used to determine how much the value has changed since the last update, which is important for the Derivative part of PID, focusing on the rate of change.
        d_value = current_value - (
            self._last_value if (self._last_value is not None) else current_value
        )
        # error calculates the difference between the setpoint (the desired value) and the current reading. It's used for both the Proportional part, which directly corrects based on current error, and the Integral part, which corrects accumulated error over time.
        error = self.config.setpoint - current_value
        # Show the values of the K's
        self.logger.debug(f"===> Kp: {self._Kp}, Ki: {self.Ki}, Kd: {self.Kd}")
        self._compute_terms(d_value, error, dt)

        seconds_on = self._calc_seconds_on(current_value)

        # Used for determining the proportional error (distance from current to last, i.e.: (current - last) / (time between the two) = slope)
        self._last_value = current_value

        self.logger.debug(
            f"-----------------\nCurrent value: {current_value}\nSeconds on: {seconds_on}\nError: {error:.2f}\nP: {self._proportional:.2f}\nI: {self._integral:.2f}\nD: {self._derivative:.2f}\n-----------------"
        )
        current_pid_state = self._set_current_pid_state(self._proportional, self._integral, self._derivative, current_value,seconds_on)
        self.logger.debug(f"--------------------\nPID State:\n{current_pid_state.model_dump_json(indent=4)}")
        loop = asyncio.get_running_loop()
        loop.create_task(self.callback(current_pid_state))


        return seconds_on

    def _calc_seconds_on(self, current_value:float) -> int:
        # In the case of co2, if the current_value is over the setpoint, there is too much co2.  We don't have an actuator to take co2 out, so return 0 seconds on.
        # In the case of humidity, if the humidity is less than the setpoint, there is too much mist in the air. We don't have a dehumidifier, so return 0 seconds on.
        # A comparison function is abstracted because one time the check is less than, the other time it is greater than.
        self.logger.debug(
            f"The current value: {current_value}. The setpoint value: {self.config.setpoint}"
        )
        if self.comparison_func(current_value, self.config.setpoint): # vpd -> current value < setpoint? CO2 -> current_value > setpoint? (return 0)
            return 0

        n_seconds = self._proportional + self._integral + self._derivative

        # The maximum amount to turn on an actuator is set by this property.  It is a safeguard so that the actuator don't stay on indefinately/too long.
        n_seconds = _clamp(n_seconds, self.seconds_on_limit)
        return n_seconds

    def _compute_terms(self, d_value, error, dt):
        """Compute the integral and derivative terms.  Clamp the integral term to prevent it from growing too large."""
        # Compute integral and derivative terms
        # Since we are not using PID during the night, we reset the error terms and start over.
        self._proportional = self._Kp * error
        self._integral += self._Ki* error * dt
        self._integral = self.sign * _clamp(abs(self._integral), self.config.integral_limits)
        self._derivative = self.sign * self._Kd* d_value / dt

    def _set_current_pid_state(self, p_error, i_error, d_error, value, seconds_on)  -> PIDState:
        return PIDState(
            value = value,
            error=p_error + i_error + d_error,
            seconds_on = seconds_on,
            P=p_error,
            I=i_error,
            D=d_error,
            Kp=self._Kp,
            Ki=self._Ki,
            Kd=self._Kd
        )


    @property
    def Kp(self):
        return self._Kp

    @Kp.setter
    def Kp(self, Kp):
        self._Kp = Kp

    @property
    def Ki(self):
        return self._Ki

    @Ki.setter
    def Ki(self, Ki):
        self._Ki= Ki

    @property
    def Kd(self):
        return self._Kd

    @Kd.setter
    def Kd(self, Kd):
        self._Kd= Kd


    @property
    def seconds_on_limit(self):
        """
        The current output limits as a 2-tuple: (lower, upper).

        See also the *seconds_on_limit* parameter in :meth:`PID.__init__`.
        """
        return self.config.seconds_on_limit

    @seconds_on_limit.setter
    def seconds_on_limit(self, limits):
        """Set the output limits."""

        self.config.seconds_on_limit = limits
