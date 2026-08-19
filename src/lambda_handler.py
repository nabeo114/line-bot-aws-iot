import base64
import hashlib
import hmac
import json
import logging
import os
import re
import urllib.error
import urllib.request

import boto3

from .ac_remote import AcRemote
from .env_monitor import EnvMonitor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ac_remote = None
env_monitor = None
channel_secret = None
channel_access_token = None
runtime_initialized = False
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
VALID_TEMPERATURE_PATTERN = re.compile(r"(2[0-9]|30)℃")

TEMPERATURE_QUICK_REPLY_ITEMS = [
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

DEFAULT_QUICK_REPLY_ITEMS = [
    {"type": "action", "action": {"type": "message", "label": "オン", "text": "オン"}},
    {"type": "action", "action": {"type": "message", "label": "オフ", "text": "オフ"}},
    {"type": "action", "action": {"type": "message", "label": "冷房", "text": "冷房"}},
    {"type": "action", "action": {"type": "message", "label": "ドライ", "text": "ドライ"}},
    {"type": "action", "action": {"type": "message", "label": "暖房", "text": "暖房"}},
    {"type": "action", "action": {"type": "message", "label": "温度", "text": "温度"}},
    {"type": "action", "action": {"type": "message", "label": "室内環境", "text": "室内環境"}},
]


def _get_ssm_parameters(parameter_names):
    # Read SecureString values from SSM at runtime to avoid hardcoding secrets.
    region_name = os.getenv("Region") or os.getenv("AWS_REGION")
    ssm = boto3.client("ssm", region_name=region_name) if region_name else boto3.client("ssm")
    response = ssm.get_parameters(Names=parameter_names, WithDecryption=True)
    invalid_parameters = response.get("InvalidParameters", [])
    if invalid_parameters:
        raise RuntimeError(f"SSM parameters not found: {invalid_parameters}")

    return {parameter["Name"]: parameter["Value"] for parameter in response["Parameters"]}


def _load_line_credentials():
    # Keep backward compatibility: plain env vars work, but SSM param names take precedence.
    secret = os.getenv("LINE_CHANNEL_SECRET", None)
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)

    secret_param_name = os.getenv("LINE_CHANNEL_SECRET_PARAM", None)
    token_param_name = os.getenv("LINE_CHANNEL_ACCESS_TOKEN_PARAM", None)

    parameter_names = [name for name in (secret_param_name, token_param_name) if name]
    if parameter_names:
        parameters = _get_ssm_parameters(parameter_names)
        if secret_param_name:
            secret = parameters.get(secret_param_name)
        if token_param_name:
            token = parameters.get(token_param_name)

    return secret, token


# get channel_secret and channel_access_token from your environment variable
def _initialize_runtime():
    global ac_remote
    global channel_access_token
    global channel_secret
    global env_monitor
    global runtime_initialized

    if runtime_initialized:
        return

    secret, token = _load_line_credentials()
    if secret is None:
        raise RuntimeError("Specify LINE_CHANNEL_SECRET or LINE_CHANNEL_SECRET_PARAM as environment variable.")
    if token is None:
        raise RuntimeError(
            "Specify LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_ACCESS_TOKEN_PARAM as environment variable."
        )

    channel_secret = secret
    channel_access_token = token
    ac_remote = AcRemote()
    env_monitor = EnvMonitor()
    runtime_initialized = True


def _parse_webhook_events(body):
    if not isinstance(body, str):
        raise ValueError("Request body must be a string")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")

    events = payload.get("events", [])
    if not isinstance(events, list):
        raise ValueError("Webhook payload 'events' must be a list")

    return events


def _send_line_reply(reply_token, message_body):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + channel_access_token,
    }
    payload = {
        "replyToken": reply_token,
        "messages": message_body,
    }

    request = urllib.request.Request(
        LINE_REPLY_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            response_body = response.read().decode("utf-8")
            if response_body != "{}":
                logger.info(response_body)
        return True
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("LINE API HTTP error: status=%s body=%s", exc.code, error_body)
    except urllib.error.URLError as exc:
        logger.error("LINE API network error: %s", exc)
    except TimeoutError:
        logger.error("LINE API request timed out")

    return False


def _handle_power_on():
    ac_remote.set_power_on()
    logger.info("Triggering publish to shadow topic to set power to ON")
    return [{"type": "text", "text": "電源をオンにしました。"}]


def _handle_power_off():
    ac_remote.set_power_off()
    logger.info("Triggering publish to shadow topic to set power to OFF")
    return [{"type": "text", "text": "電源をオフにしました。"}]


def _handle_mode_cool():
    ac_remote.set_mode_cool()
    logger.info("Triggering publish to shadow topic to set mode to Cool")
    return [{"type": "text", "text": "冷房にしました。"}]


def _handle_mode_dry():
    ac_remote.set_mode_dry()
    logger.info("Triggering publish to shadow topic to set mode to Dry")
    return [{"type": "text", "text": "ドライにしました。"}]


def _handle_mode_heat():
    ac_remote.set_mode_heat()
    logger.info("Triggering publish to shadow topic to set mode to Heat")
    return [{"type": "text", "text": "暖房にしました。"}]


def _handle_temperature_prompt():
    return [
        {
            "type": "text",
            "text": "何度にしますか？",
            "quickReply": {"items": TEMPERATURE_QUICK_REPLY_ITEMS},
        }
    ]


def _handle_indoor_environment():
    env_snapshot = env_monitor.get_snapshot()
    return [
        {
            "type": "text",
            "text": (
                "室内環境は\n"
                f"温度：{round(env_snapshot['temperature'], 1)}℃\n"
                f"湿度：{round(env_snapshot['humidity'], 1)}%\n"
                f"気圧：{round(env_snapshot['pressure'], 1)}hPa\n"
                "です。"
            ),
        }
    ]


def _handle_default_status():
    ac_state = ac_remote.get_state()
    env_snapshot = env_monitor.get_snapshot()
    return [
        {
            "type": "text",
            "text": (
                "エアコンは\n"
                f"電源：{ac_state['power']}\n"
                f"モード：{ac_state['mode']}\n"
                f"温度：{ac_state['temperature']}℃\n"
                "に設定されています。\n"
                f"室温は{round(env_snapshot['temperature'], 1)}℃です。\n"
                "ご用件は何ですか？"
            ),
            "quickReply": {"items": DEFAULT_QUICK_REPLY_ITEMS},
        }
    ]


def _handle_set_temperature(temperature):
    ac_remote.set_temperature(temperature)
    logger.info("Triggering publish to shadow topic to set temperature")
    return [{"type": "text", "text": f"{ac_remote.get_temperature(refresh=False)}℃にしました。"}]


def _parse_temperature_command(message_text):
    if VALID_TEMPERATURE_PATTERN.match(message_text) is None:
        return None
    return int(message_text.replace("℃", ""))


COMMAND_ROUTER = {
    "オン": _handle_power_on,
    "オフ": _handle_power_off,
    "冷房": _handle_mode_cool,
    "ドライ": _handle_mode_dry,
    "暖房": _handle_mode_heat,
    "温度": _handle_temperature_prompt,
    "室内環境": _handle_indoor_environment,
}


def lambda_handler(event, context):
    try:
        _initialize_runtime()
    except Exception:
        logger.exception("Runtime initialization failed")
        return {"statusCode": 500, "body": "{}"}

    logger.info(json.dumps(event))

    body = event.get("body", "")
    if not isinstance(body, str):
        logger.error("Invalid request body type: %s", type(body).__name__)
        return {"statusCode": 400, "body": "{}"}

    hash = hmac.new(channel_secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode("utf-8")
    headers = event.get("headers") or {}
    if not isinstance(headers, dict):
        headers = {}

    # Verify LINE request signature before processing webhook events.
    if not hmac.compare_digest(signature, headers.get("X-Line-Signature", "")) and not hmac.compare_digest(
        signature, headers.get("x-line-signature", "")
    ):
        logger.error("validate NG")
        return {"statusCode": 403, "body": "{}"}

    try:
        events = _parse_webhook_events(body)
    except ValueError as exc:
        logger.error("Invalid webhook payload: %s", exc)
        return {"statusCode": 400, "body": "{}"}

    # Each text message event maps to one AC/shadow operation and one LINE reply.
    for event_data in events:
        if not isinstance(event_data, dict):
            logger.warning("Skip non-object event payload: %s", event_data)
            continue

        if event_data.get("type") != "message":
            continue

        message = event_data.get("message") or {}
        if not isinstance(message, dict):
            logger.warning("Skip event with invalid message payload: %s", event_data)
            continue

        if message.get("type") != "text":
            continue

        reply_token = event_data.get("replyToken")
        if not isinstance(reply_token, str) or not reply_token:
            logger.warning("Skip event without valid replyToken: %s", event_data)
            continue

        message_text = message.get("text")
        if not isinstance(message_text, str):
            logger.warning("Skip event with non-string text: %s", event_data)
            continue

        try:
            temperature = _parse_temperature_command(message_text)
            if temperature is not None:
                message_body = _handle_set_temperature(temperature)
            else:
                handler = COMMAND_ROUTER.get(message_text, _handle_default_status)
                message_body = handler()
        except Exception:
            logger.exception("Failed to process event payload")
            continue

        if not _send_line_reply(reply_token=reply_token, message_body=message_body):
            logger.error("Failed to send reply for replyToken=%s", reply_token)

    return {"statusCode": 200, "body": "{}"}
