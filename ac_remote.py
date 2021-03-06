import logging
import os
import boto3
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class AcRemote:
    def __init__(self):
        self.client = boto3.client('iot-data', region_name=os.environ['Region'])
        self.thingName = os.environ['ThingName']
        
        self.update_data()

    def set_power_on(self):
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"power":1}}}')
        self.power = 1

    def set_power_off(self):
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"power":0}}}')
        self.power = 0

    def set_temperature(self, temperature):
        if temperature < 20:
            temperature = 20
        if temperature > 30:
            temperature = 30
        
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"temp":' + str(int(temperature)) + '}}}')
        self.temp = temperature

    def set_mode_heat(self):
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"mode":1}}}')
        self.mode = 1

    def set_mode_dry(self):
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"mode":2}}}')
        self.mode = 2

    def set_mode_cool(self):
        self.client.update_thing_shadow(thingName = self.thingName, payload = '{"state":{"desired":{"mode":3}}}')
        self.mode = 3

    def get_power(self):
        self.update_data()
        if self.power == 1:
            return "ON"
        else:
            return "OFF"

    def get_temperature(self):
        self.update_data()
        return self.temp

    def get_mode(self):
        self.update_data()
        if self.mode == 1:
            return "HEAT"
        elif self.mode == 2:
            return "DRY"
        elif self.mode == 3:
            return "COOL"
        else:
            return "COOL"

    def update_data(self):
        response = self.client.get_thing_shadow(thingName = self.thingName)
        streamingBody = response["payload"]
        shadow_data = json.loads(streamingBody.read())
        logger.info(shadow_data)
        self.power = shadow_data["state"]["desired"]["power"]
        self.temp = shadow_data["state"]["desired"]["temp"]
        self.mode = shadow_data["state"]["desired"]["mode"]
