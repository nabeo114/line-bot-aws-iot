import base64
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import urllib.request

import boto3

from .ac_remote import AcRemote
from .env_monitor import EnvMonitor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ac_remote = AcRemote()
env_monitor = EnvMonitor()


def _get_ssm_parameter(parameter_name):
    # Read SecureString values from SSM at runtime to avoid hardcoding secrets.
    region_name = os.getenv("Region") or os.getenv("AWS_REGION")
    ssm = boto3.client("ssm", region_name=region_name) if region_name else boto3.client("ssm")
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    return response["Parameter"]["Value"]


def _load_line_credentials():
    # Keep backward compatibility: plain env vars work, but SSM param names take precedence.
    secret = os.getenv("LINE_CHANNEL_SECRET", None)
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)

    secret_param_name = os.getenv("LINE_CHANNEL_SECRET_PARAM", None)
    token_param_name = os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PARAM", None)

    if secret_param_name:
        secret = _get_ssm_parameter(secret_param_name)
    if token_param_name:
        token = _get_ssm_parameter(token_param_name)

    return secret, token


# get channel_secret and channel_access_token from your environment variable
channel_secret, channel_access_token = _load_line_credentials()
if channel_secret is None:
    logger.error("Specify LINE_CHANNEL_SECRET or LINE_CHANNEL_SECRET_PARAM as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    logger.error("Specify LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_ACCESS_TOKEN_PARAM as environment variable.")
    sys.exit(1)


def lambda_handler(event, context):
    logger.info(json.dumps(event))

    body = event.get("body", "")  # Request body string
    hash = hmac.new(channel_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode("utf-8")
    headers = event.get("headers") or {}
    # Verify LINE request signature before processing webhook events.
    if not hmac.compare_digest(signature, headers.get("X-Line-Signature", "")) and not hmac.compare_digest(
        signature, headers.get("x-line-signature", "")
    ):
        logger.error("validate NG")
        return {"statusCode": 403, "body": "{}"}

    # Each text message event maps to one AC/shadow operation and one LINE reply.
    for event_data in json.loads(body).get("events", []):
        if event_data["type"] != "message":
            continue

        if event_data["message"]["type"] != "text":
            continue

        message_text = event_data["message"]["text"]
        valid_temperature = r"(2[0-9]|30)℃"

        if message_text == "オン":
            ac_remote.set_power_on()
            logger.info("Triggering publish to shadow topic to set power to ON")
            message_body = [{"type": "text", "text": "電源をオンにしました。"}]
        elif message_text == "オフ":
            ac_remote.set_power_off()
            logger.info("Triggering publish to shadow topic to set power to OFF")
            message_body = [{"type": "text", "text": "電源をオフにしました。"}]
        elif message_text == "冷房":
            ac_remote.set_mode_cool()
            logger.info("Triggering publish to shadow topic to set mode to Cool")
            message_body = [{"type": "text", "text": "冷房にしました。"}]
        elif message_text == "ドライ":
            ac_remote.set_mode_dry()
            logger.info("Triggering publish to shadow topic to set mode to Dry")
            message_body = [{"type": "text", "text": "ドライにしました。"}]
        elif message_text == "暖房":
            ac_remote.set_mode_heat()
            logger.info("Triggering publish to shadow topic to set mode to Heat")
            message_body = [{"type": "text", "text": "暖房にしました。"}]
        elif message_text == "温度":
            message_body = [
                {
                    "type": "text",
                    "text": "何度にしますか？",
                    "quickReply": {
                        "items": [
                            {"type": "action", "action": {"type": "message", "label": "20℃", "text": "20℃"}},
                            {"type": "action", "action": {"type": "message", "label": "21℃", "text": "21℃"}},
                            {"type": "action", "action": {"type": "message", "label": "22℃", "text": "22℃"}},
                            {"type": "action", "action": {"type": "message", "label": "23℃", "text": "23℃"}},
                            {"type": "action", "action": {"type": "message", "label": "24℃", "text": "24℃"}},
                            {"type": "action", "action": {"type": "message", "label": "25℃", "text": "25℃"}},
                            {"type": "action", "action": {"type": "message", "label": "26℃", "text": "26℃"}},
                            {"type": "action", "action": {"type": "message", "label": "27℃", "text": "27℃"}},
                            {"type": "action", "action": {"type": "message", "label": "28℃", "text": "28℃"}},
                            {"type": "action", "action": {"type": "message", "label": "29℃", "text": "29℃"}},
                            {"type": "action", "action": {"type": "message", "label": "30℃", "text": "30℃"}},
                        ]
                    },
                }
            ]
        elif re.match(valid_temperature, message_text) is not None:
            ac_remote.set_temperature(int(message_text.replace("℃", "")))
            logger.info("Triggering publish to shadow topic to set temperature")
            message_body = [{"type": "text", "text": f"{ac_remote.get_temperature()}℃にしました。"}]
        elif message_text == "室内環境":
            env_temperature = env_monitor.get_temperature()
            env_humidity = env_monitor.get_humidity()
            env_pressure = env_monitor.get_pressure()
            message_body = [
                {
                    "type": "text",
                    "text": (
                        "室内環境は\n"
                        f"温度：{round(env_temperature, 1)}℃\n"
                        f"湿度：{round(env_humidity, 1)}%\n"
                        f"気圧：{round(env_pressure, 1)}hPa\n"
                        "です。"
                    ),
                }
            ]
        else:
            ac_power = ac_remote.get_power()
            ac_mode = ac_remote.get_mode()
            ac_temperature = ac_remote.get_temperature()
            env_temperature = env_monitor.get_temperature()
            message_body = [
                {
                    "type": "text",
                    "text": (
                        "エアコンは\n"
                        f"電源：{ac_power}\n"
                        f"モード：{ac_mode}\n"
                        f"温度：{ac_temperature}℃\n"
                        "に設定されています。\n"
                        f"室温は{round(env_temperature, 1)}℃です。\n"
                        "ご用件は何ですか？"
                    ),
                    "quickReply": {
                        "items": [
                            {"type": "action", "action": {"type": "message", "label": "オン", "text": "オン"}},
                            {"type": "action", "action": {"type": "message", "label": "オフ", "text": "オフ"}},
                            {"type": "action", "action": {"type": "message", "label": "冷房", "text": "冷房"}},
                            {"type": "action", "action": {"type": "message", "label": "ドライ", "text": "ドライ"}},
                            {"type": "action", "action": {"type": "message", "label": "暖房", "text": "暖房"}},
                            {"type": "action", "action": {"type": "message", "label": "温度", "text": "温度"}},
                            {"type": "action", "action": {"type": "message", "label": "室内環境", "text": "室内環境"}},
                        ]
                    },
                }
            ]

        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + channel_access_token,
        }
        body = {
            "replyToken": event_data["replyToken"],
            "messages": message_body,
        }
        # Send reply through LINE Messaging API.
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
        with urllib.request.urlopen(req) as res:
            res_body = res.read().decode("utf-8")
            if res_body != "{}":
                logger.info(res_body)

    return {"statusCode": 200, "body": "{}"}
