#! /usr/bin/python3.7


'''
    Tests should cover:
        * Proper application logic
        * Information is being properly processed and validated
        * Minimal side effects and seperation of concerns are preserved
'''

from unittest import mock
from saltbot.saltbot import SaltBot
from urllib.parse import urlparse
import random
import requests
import unittest
import time

GLOBAL_START = time.time()

SITE_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip,deflate br',
    'Host': 'www.saltybet.com',
    'Referer': 'https://www.saltybet.com/',
    'Content-Type': 'application/json; charset=utf-8',
    'DNT': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0',
    'X-Requested-With': 'XMLHttpRequest',
    'Connection': 'keep-alive'
}
STATE_RESP_LOCKED = {
    "p1name": "Kris",
    "p2name": "Ryu EX3",
    "p1total": "1,603,918",
    "p2total": "1,863,115",
    "status": "locked",
    "alert": "",
    "x": 1,
    "remaining": "18 more matches until the next tournament!"
}

STATE_RESP_OPEN = {
    "p1name": "Kris",
    "p2name": "Ryu EX3",
    "p1total": "0",
    "p2total": "0",
    "status": "open",
    "alert": "",
    "x": 0,
    "remaining": "18 more matches until the next tournament!"
}

STATE_RESP_WON = {
    "p1name": "Kris",
    "p2name": "Ryu EX3",
    "p1total": "1,603,918",
    "p2total": "1,863,115",
    "status": "2",
    "alert": "",
    "x": 1,
    "remaining": "17 more matches until the next tournament!"}

ZDATA_RESP = {
    "624134": {
        "n": "anthraxlol",
        "b": "160596752", "p": "1", "w": "150700",
        "r": "0434a2f9039cf67325ec519933f2476d",
        "g": "1", "c": "239,255,0"},
    "399392": {
        "n": "raggedclaws",
        "b": "4541155", "p": "2", "w": "6358",
        "r": "20", "g": "0", "c": "0"},
    "641032": {
        "n": "cptodinsbutt",
        "b": "1498", "p": "2", "w": "25",
        "r": "3", "g": "0", "c": "0"},
    "497924": {
        "n": "Morphemec",
        "b": "241480", "p": "2", "w": "1213",
        "r": "17", "g": "0", "c": "0"},
    "639735": {
        "n": "GuiltyGoob",
        "b": "1948", "p": "2", "w": "195",
        "r": "4", "g": "0", "c": "0"},
    "44991": {
        "n": "jimmyfranks",
        "b": "131184", "p": "2", "w": "5550",
        "r": "4a3da0b1e6f269fcab301250427cfc34",
        "g": "1", "c": "0"},
    "455375": {
        "n": "HateHorror",
        "b": "51892", "p": "2", "w": "680",
        "r": "19", "g": "1", "c": "0"}}
ZDATA_RESP.update(STATE_RESP_LOCKED)

ZDATA_EXPIRED = {
    "p1name": "Ringlerun",
    "p2name": "Rolento f. schugerg",
    "p1total": "1,676,717",
    "p2total": "1,041,053",
    "status": "2",
    "alert": "",
    "x": 1,
    "remaining": "16 more matches until the next tournament!",
    "68374": {"n": "Justystuff", "b": "575"},
    "588965": {"n": "FutaClaws", "b": "4612953"},
    "63785": {"n": "Jofahren", "b": "3565441"},
    "29275": {"n": "TheRedKirby", "b": "14273841"},
    "123911": {"n": "shetaron", "b": "2433827"}}
COOKIES = {'__cfduid': 'd38637fd5fcdd51ba17c23f4f34fd12be1566670847', 'PHPSESSID': 'f3240botpio78qaqjqa75os9q7'}


def requests_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json, status_code, cookies):
            self.json_data = json
            self.status_code = status_code
            self.cookies = cookies

        def json(self):
            return self.json_data

        class elapsed:

            def total_seconds():
                return 2

    timeout = kwargs.get('timeout', None)

    # 35% chance to throw a timeout error
    if timeout:
        if timeout < 16:
            if random.randint(0, 100) < 35:
                raise requests.exceptions.ReadTimeout

    url = urlparse(args[0])
    if "https://www.saltybet.com/" == url.scheme + "://" + url.netloc + '/':
        headers = kwargs.get('headers')
        if headers is None:
            return MockResponse('', 403, {})
        for k, v in headers.items():
            if k not in SITE_HEADERS.keys():
                return MockResponse('', 403, {})
            elif SITE_HEADERS[k] != v:
                return MockResponse('', 403, {})

        if url.path in ['/', '']:
            return MockResponse(
                '', 200, COOKIES)
        else:
            cookies = kwargs.get('cookies')
            if cookies is None:
                return MockResponse('', 403, {})

            for k, v in COOKIES.items():
                if k not in cookies.keys():
                    return MockResponse('', 403, {})
                elif cookies[k] != COOKIES[k]:
                    return MockResponse('', 403, {})

            if 't' not in kwargs.get('params').keys():
                return MockResponse(None, 404, {})

            if url.path.lstrip('/') == 'state.json':
                # Match should last about 15 seconds
                # Not reality but I don't want super long tests
                if 8 > time.time() - GLOBAL_START:
                    return MockResponse(STATE_RESP_OPEN, 200, {})
                elif 12 > time.time() - GLOBAL_START > 8:
                    return MockResponse(STATE_RESP_LOCKED, 200, {})
                else:
                    return MockResponse(STATE_RESP_WON, 200, {})

            elif url.path.lstrip('/') == 'zdata.json':
                if 8 > time.time() - GLOBAL_START:
                    return MockResponse(ZDATA_RESP, 200, {})
                else:
                    return MockResponse(ZDATA_EXPIRED, 200, {})

    return MockResponse(None, 404, {})


class FunctionalTests(unittest.TestCase):

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_get_home(self, mock_get):
        bot = SaltBot(dbname='testing')
        bot.get('https://www.saltybet.com')
        assert bot.cookies == COOKIES

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_get_state(self, mock_get):
        bot = SaltBot(dbname='testing')
        resp = bot.get(
            'https://www.saltybet.com/state.json',
            params={'t': int(time.time())})
        assert isinstance(resp.json(), dict)

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_get_zdata(self, mock_get):
        bot = SaltBot(dbname='testing')
        resp = bot.get(
            'https://www.saltybet.com/zdata.json',
            params={'t': int(time.time())})
        assert isinstance(resp.json(), dict)

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_get_bad_state(self, mock_get):
        bot = SaltBot(dbname='testing')
        self.assertRaises(Exception, bot.get, 'https://www.saltybet.com/state.json')

    @mock.patch('requests.get', side_effect=requests_mock)
    def test_get_bad_zdata(self, mock_get):
        bot = SaltBot(dbname='testing')
        self.assertRaises(Exception, bot.get, 'https://www.saltybet.com/zdata.json')
