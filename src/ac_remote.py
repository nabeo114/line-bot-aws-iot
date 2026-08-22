import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class AcRemote:
    def __init__(self):
        # IoT Data Plane client is used to read/write the thing shadow desired state.
        self.client = boto3.client("iot-data", region_name=os.environ["Region"])
        self.thing_name = os.environ["ThingName"]
        self.power = 0
        self.temp = 24
        self.mode = 3

        self.update_data()

    def set_power_on(self):
        self._update_desired_state({"power": 1})
        self.power = 1

    def set_power_off(self):
        self._update_desired_state({"power": 0})
        self.power = 0

    def set_temperature(self, temperature):
        # Clamp to the AC-supported temperature range.
        if temperature < 20:
            temperature = 20
        if temperature > 30:
            temperature = 30

        self._update_desired_state({"temp": int(temperature)})
        self.temp = temperature

    def set_mode_heat(self):
        self._update_desired_state({"mode": 1})
        self.mode = 1

    def set_mode_dry(self):
        self._update_desired_state({"mode": 2})
        self.mode = 2

    def set_mode_cool(self):
        self._update_desired_state({"mode": 3})
        self.mode = 3

    def _update_desired_state(self, desired_patch):
        payload = json.dumps({"state": {"desired": desired_patch}})
        self.client.update_thing_shadow(thingName=self.thing_name, payload=payload)

    def get_state(self, refresh=True):
        if refresh:
            self.update_data()
        return {
            "power": "ON" if self.power == 1 else "OFF",
            "temperature": self.temp,
            "mode": self._mode_to_text(self.mode),
        }

    def get_power(self, refresh=True):
        return self.get_state(refresh=refresh)["power"]

    def get_temperature(self, refresh=True):
        return self.get_state(refresh=refresh)["temperature"]

    def get_mode(self, refresh=True):
        return self.get_state(refresh=refresh)["mode"]

    def _mode_to_text(self, mode):
        if mode == 1:
            return "HEAT"
        if mode == 2:
            return "DRY"
        if mode == 3:
            return "COOL"
        return "COOL"

    def update_data(self):
        # Prefer reported values (actual device state) and fall back to desired values.
        response = self.client.get_thing_shadow(thingName=self.thing_name)
        streaming_body = response["payload"]
        shadow_data = json.loads(streaming_body.read())
        logger.info(shadow_data)

        state = shadow_data.get("state", {})
        desired = state.get("desired", {})
        reported = state.get("reported", {})

        self.power = reported.get("power", desired.get("power", self.power))
        self.temp = reported.get("temp", desired.get("temp", self.temp))
        self.mode = reported.get("mode", desired.get("mode", self.mode))
