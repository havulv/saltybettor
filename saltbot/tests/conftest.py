#! /usr/bin/env python3

from urllib.parse import urlparse
import pytest
import random
import requests
import time

'''
    Requests fixture that mocks the saltybettor interface
'''


@pytest.fixture
def global_start():
    return time.time()


@pytest.fixture
def site_headers():
    return {
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


@pytest.fixture
def state_resp_locked():
    return {
        "p1name": "Kris",
        "p2name": "Ryu EX3",
        "p1total": "1,603,918",
        "p2total": "1,863,115",
        "status": "locked",
        "alert": "",
        "x": 1,
        "remaining": "18 more matches until the next tournament!"
    }


@pytest.fixture
def state_resp_open():
    return {
        "p1name": "Kris",
        "p2name": "Ryu EX3",
        "p1total": "0",
        "p2total": "0",
        "status": "open",
        "alert": "",
        "x": 0,
        "remaining": "18 more matches until the next tournament!"
    }


@pytest.fixture
def state_resp_won():
    return {
        "p1name": "Kris",
        "p2name": "Ryu EX3",
        "p1total": "1,603,918",
        "p2total": "1,863,115",
        "status": "2",
        "alert": "",
        "x": 1,
        "remaining": "17 more matches until the next tournament!"
    }


@pytest.fixture
def zdata_resp(state_resp_locked):
    zdata = {
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
    zdata.update(state_resp_locked)
    return zdata


@pytest.fixture
def zdata_expired():
    return {
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
        "123911": {"n": "shetaron", "b": "2433827"}
    }


@pytest.fixture
def site_cookies():
    return {
        '__cfduid': 'd38637fd5fcdd51ba17c23f4f34fd12be1566670847',
        'PHPSESSID': 'f3240botpio78qaqjqa75os9q7'
    }


@pytest.fixture(scope='function')
def silent_requests(
        site_headers, zdata_resp,
        site_cookies, state_resp_open, state_resp_locked,
        state_resp_won, zdata_expired, monkeypatch, global_start):
    def mock_get(*args, **kwargs):
        class MockResponse:
            def __init__(self, json, status_code, cookies):
                self.json_data = json
                self.status_code = status_code
                self.cookies = cookies

            def json(self):
                return self.json_data

            class Elapsed:

                def total_seconds():
                    return 2

        timeout = kwargs.get('timeout', None)

        # 35% chance to throw a timeout error
        if timeout:
            if timeout < 16:
                if random.randint(0, 100) < 35:
                    raise requests.exceptions.ReadTimeout

        url = urlparse(args[1])
        if "https://www.saltybet.com/" == (url.scheme + "://" + url.netloc + '/'):
            headers = kwargs.get('headers')
            if headers is None:
                return MockResponse('', 403, {})
            for k, v in headers.items():
                if k not in site_headers.keys():
                    return MockResponse('', 403, {})
                elif site_headers[k] != v:
                    return MockResponse('', 403, {})

            if url.path in ['/', '']:
                return MockResponse(
                    '', 200, site_cookies)
            else:
                cookies = kwargs.get('cookies')
                if cookies is None:
                    return MockResponse('', 403, {})

                for k, v in site_cookies.items():
                    if k not in cookies.keys():
                        return MockResponse('', 403, {})
                    elif cookies[k] != site_cookies[k]:
                        return MockResponse('', 403, {})

                if 't' not in kwargs.get('params').keys():
                    return MockResponse(None, 404, {})

                if url.path.lstrip('/') == 'state.json':
                    # Match should last about 15 seconds
                    # Not reality but I don't want super long tests
                    if 8 > time.time() - global_start:
                        return MockResponse(state_resp_open, 200, {})
                    elif 12 > time.time() - global_start > 8:
                        return MockResponse(state_resp_locked, 200, {})
                    else:
                        return MockResponse(state_resp_won, 200, {})

                elif url.path.lstrip('/') == 'zdata.json':
                    if 8 > time.time() - global_start:
                        return MockResponse(zdata_resp, 200, {})
                    else:
                        return MockResponse(zdata_expired, 200, {})

        return MockResponse(None, 404, {})

    monkeypatch.setattr(requests.Session, 'get', mock_get)


'''
    Database fixture that mocks database calls
'''
