#!/usr/bin/env python
# -*- encoding=utf8 -*-

import json
import random
import time

import requests

USER_AGENTS = [
    "JD4iPhone/12345 (iPhone; iOS; Scale/2.00);jdmall;iphone;version/12.2.0;build/12345;network/wifi;screen/750x1334;os/14.0"
]

SECKILL_PLAN = [
    "10:07:59.700",
    "11:59:59.700",
    "18:07:59.700",
    "19:59:59.700",
]


def parse_json(s):
    begin = s.find('{')
    end = s.rfind('}') + 1
    return json.loads(s[begin:end])


def get_random_useragent():
    """生成随机的UserAgent
    :return: UserAgent字符串
    """
    return random.choice(USER_AGENTS)


def get_seckill_plan(plan):
    """生成随机的抢购时间
    :return: 抢购时间字符串
    """
    return SECKILL_PLAN[plan]


def response_status(resp):
    if resp.status_code != requests.codes.OK:
        print('Status: %u, Url: %s' % (resp.status_code, resp.url))
        return False
    return True


def wait_some_time():
    time.sleep(random.randint(100, 300) / 1000)
