import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EnvMonitor:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=os.environ["Region"])
        self.table = self.dynamodb.Table(os.environ["TableName"])

        self.update_data()

    def get_temperature(self):
        return self.get_snapshot()["temperature"]

    def get_humidity(self):
        return self.get_snapshot()["humidity"]

    def get_pressure(self):
        return self.get_snapshot()["pressure"]

    def get_snapshot(self, refresh=True):
        if refresh:
            self.update_data()
        return {
            "temperature": float(self.temperature),
            "humidity": float(self.humidity),
            "pressure": float(self.pressure),
        }

    def update_data(self):
        # Read the latest sensor values from one fixed partition key/value pair.
        response = self.table.get_item(Key={os.environ["PartitionKey"]: os.environ["PartitionName"]})
        logger.info(response)
        self.temperature = response["Item"]["temperature"]
        self.humidity = response["Item"]["humidity"]
        self.pressure = response["Item"]["pressure"]
