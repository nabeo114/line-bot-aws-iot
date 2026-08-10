import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class AcRemote:
    def __init__(self):
        self.client = boto3.client("iot-data", region_name=os.environ["Region"])
        self.thing_name = os.environ["ThingName"]

        self.update_data()

    def set_power_on(self):
        self.client.update_thing_shadow(thingName=self.thing_name, payload='{"state":{"desired":{"power":1}}}')
        self.power = 1

    def set_power_off(self):
        self.client.update_thing_shadow(thingName=self.thing_name, payload='{"state":{"desired":{"power":0}}}')
        self.power = 0

    def set_temperature(self, temperature):
        if temperature < 20:
            temperature = 20
        if temperature > 30:
            temperature = 30

        self.client.update_thing_shadow(
            thingName=self.thing_name,
            payload='{"state":{"desired":{"temp":' + str(int(temperature)) + "}}}",
        )
        self.temp = temperature

    def set_mode_heat(self):
        self.client.update_thing_shadow(thingName=self.thing_name, payload='{"state":{"desired":{"mode":1}}}')
        self.mode = 1

    def set_mode_dry(self):
        self.client.update_thing_shadow(thingName=self.thing_name, payload='{"state":{"desired":{"mode":2}}}')
        self.mode = 2

    def set_mode_cool(self):
        self.client.update_thing_shadow(thingName=self.thing_name, payload='{"state":{"desired":{"mode":3}}}')
        self.mode = 3

    def get_power(self):
        self.update_data()
        if self.power == 1:
            return "ON"
        return "OFF"

    def get_temperature(self):
        self.update_data()
        return self.temp

    def get_mode(self):
        self.update_data()
        if self.mode == 1:
            return "HEAT"
        if self.mode == 2:
            return "DRY"
        if self.mode == 3:
            return "COOL"
        return "COOL"

    def update_data(self):
        response = self.client.get_thing_shadow(thingName=self.thing_name)
        streaming_body = response["payload"]
        shadow_data = json.loads(streaming_body.read())
        logger.info(shadow_data)
        self.power = shadow_data["state"]["desired"]["power"]
        self.temp = shadow_data["state"]["desired"]["temp"]
        self.mode = shadow_data["state"]["desired"]["mode"]
