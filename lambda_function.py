import sys
import logging
import os
import json

import base64
import hashlib
import hmac

import urllib.request, urllib.parse

import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from ac_remote import AcRemote
ac_remote = AcRemote()

from env_monitor import EnvMonitor
env_monitor = EnvMonitor()

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    logger.error('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    logger.error('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

def lambda_handler(event, context):
    logger.info(json.dumps(event))
    
    channel_secret = os.environ['LINE_CHANNEL_SECRET'] # Channel secret string
    body = event.get('body', '') # Request body string
    hash = hmac.new(channel_secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode('utf-8')
    # Compare X-Line-Signature request header and the signature
    if signature != event.get('headers').get('X-Line-Signature', ''):
        logger.error('validate NG')
        return {'statusCode': 403, 'body': '{}'}
    
    for event_data in json.loads(body).get('events', []):
        if event_data['type'] != 'message':
            continue
        
        if event_data['message']['type'] != 'text':
            continue
        
        message_text = event_data['message']['text']
        valid_temperature = r'(2[0-9]|30)℃'
        
        if message_text == 'オン':
            ac_remote.set_power_on()
            logger.info("Triggering publish to shadow topic to set power to ON")
            message_body = [{
                'type': 'text',
                'text': '電源をオンにしました。'
            }]
        elif message_text == 'オフ':
            ac_remote.set_power_off()
            logger.info("Triggering publish to shadow topic to set power to OFF")
            message_body = [{
                'type': 'text',
                'text': '電源をオフにしました。'
            }]
        elif message_text == '冷房':
            ac_remote.set_mode_cool()
            logger.info("Triggering publish to shadow topic to set mode to Cool")
            message_body = [{
                'type': 'text',
                'text': '冷房にしました。'
            }]
        elif message_text == 'ドライ':
            ac_remote.set_mode_dry()
            logger.info("Triggering publish to shadow topic to set mode to Dry")
            message_body = [{
                'type': 'text',
                'text': 'ドライにしました。'
            }]
        elif message_text == '暖房':
            ac_remote.set_mode_heat()
            logger.info("Triggering publish to shadow topic to set mode to Heat")
            message_body = [{
                'type': 'text',
                'text': '暖房にしました。'
            }]
        elif message_text == '温度':
            message_body = [{
                'type': 'text',
                'text': '何度にしますか？',
                'quickReply': {
                    'items': [{
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '20℃',
                            'text': '20℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '21℃',
                            'text': '21℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '22℃',
                            'text': '22℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '23℃',
                            'text': '23℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '24℃',
                            'text': '24℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '25℃',
                            'text': '25℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '26℃',
                            'text': '26℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '27℃',
                            'text': '27℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '28℃',
                            'text': '28℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '29℃',
                            'text': '29℃'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '30℃',
                            'text': '30℃'
                        }
                    }]
                }
            }]
        elif re.match(valid_temperature, message_text) is not None:
            ac_remote.set_temperature(int(message_text.replace('℃','')))
            logger.info("Triggering publish to shadow topic to set temperature")
            message_body = [{
                'type': 'text',
#                'text': message_text + 'にしました。'
                'text': str(ac_remote.get_temperature()) + '℃にしました。'
            }]
        elif message_text == '室内環境':
            env_temperature = env_monitor.get_temperature()
            env_humidity = env_monitor.get_humidity()
            env_pressure = env_monitor.get_pressure()
            message_body = [{
                'type': 'text',
                'text': '室内環境は\n温度：' + str(round(env_temperature,1)) + '℃\n湿度：' + str(round(env_humidity,1)) + '%\n気圧：' + str(round(env_pressure,1)) + 'hPa\nです。'
            }]
        else:
            ac_power = ac_remote.get_power()
            ac_mode = ac_remote.get_mode()
            ac_temperature = ac_remote.get_temperature()
            env_temperature = env_monitor.get_temperature()
            message_body = [{
                'type': 'text',
                'text': 'エアコンの設定は\n電源：' + ac_power + '\nモード：' + ac_mode + '\n温度：' + str(ac_temperature) + '℃\nです。\n室温は' + str(round(env_temperature,1)) + '℃です。\nご用件は何ですか？',
                'quickReply': {
                    'items': [{
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': 'オン',
                            'text': 'オン'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': 'オフ',
                            'text': 'オフ'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '冷房',
                            'text': '冷房'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': 'ドライ',
                            'text': 'ドライ'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '暖房',
                            'text': '暖房'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '温度',
                            'text': '温度'
                        }
                    },
                    {
                        'type': 'action',
                        'action': {
                            'type': 'message',
                            'label': '室内環境',
                            'text': '室内環境'
                        }
                    }]
                }
            }]
        
        url = 'https://api.line.me/v2/bot/message/reply'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + channel_access_token,
        }
        body = {
            'replyToken': event_data['replyToken'],
            'messages': message_body
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), method='POST', headers=headers)
        with urllib.request.urlopen(req) as res:
            res_body = res.read().decode('utf-8')
            if res_body != '{}':
                logger.info(res_body)
    
    return {'statusCode': 200, 'body': '{}'}
