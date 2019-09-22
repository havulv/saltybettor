#! /usr/bin/env python3

from saltbot import database
from urllib.parse import urlparse
from requests import cookies
import requests
import pytest
import random
import time

'''
    Requests fixture that mocks the saltybettor interface for saltbot
'''


@pytest.fixture
def global_start():
    return time.time()


@pytest.fixture
def site_headers():
    return {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
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
    jar = cookies.RequestsCookieJar()
    jar.set_cookie(cookies.create_cookie(
        name='__cfduid',
        value='d38637fd5fcdd51ba17c23f4f34fd12be1566670847',
    ))
    jar.set_cookie(cookies.create_cookie(
        name='PHPSESSID',
        value='f3240botpio78qaqjqa75os9q7',
    ))
    return jar


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

            class elapsed:

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
            headers = kwargs.get('headers') or args[0].headers
            if headers is None:
                return MockResponse('', 403, {})
            for k, v in headers.items():
                if k not in site_headers.keys():
                    return MockResponse('', 403, {})
                elif site_headers[k] != v:
                    return MockResponse('', 403, {})

            if url.path in ['/', '']:
                if hasattr(args[0], 'cookies'):
                    args[0].cookies = site_cookies
                return MockResponse(
                    '', 200, site_cookies)
            else:
                cookies = kwargs.get('cookies') or args[0].cookies
                if cookies is None:
                    return MockResponse('', 403, {})

                for k, v in site_cookies.items():
                    if k not in cookies.keys():
                        return MockResponse('', 403, {})
                    elif cookies[k] != site_cookies[k]:
                        return MockResponse('', 403, {})

                if 't' not in kwargs.get('params').keys():
                    return MockResponse(None, 404, {})

                match_cycle_time = int(time.time() - global_start) % 20
                if url.path.lstrip('/') == 'state.json':
                    # Match should last about 15 seconds
                    # Not reality but I don't want super long tests
                    if 8 > match_cycle_time:
                        return MockResponse(state_resp_open, 200, {})
                    elif 12 > match_cycle_time > 8:
                        return MockResponse(state_resp_locked, 200, {})
                    else:
                        return MockResponse(state_resp_won, 200, {})

                elif url.path.lstrip('/') == 'zdata.json':
                    if 8 > match_cycle_time:
                        return MockResponse(zdata_resp, 200, {})
                    else:
                        return MockResponse(zdata_expired, 200, {})

        return MockResponse(None, 404, {})

    monkeypatch.setattr(requests.Session, 'get', mock_get)


'''
    Database fixture that mocks the calls to Betdbfor saltbot
        -- pretty simple, but needs to be built out more if we
           want to do extensive error checking and model the behavior
           correctly.
        -- we don't want an actual database because we are not testing
           the actual database calls, and are instead testing the database
           api calls from the application
'''


@pytest.fixture(scope='function')
def silent_database(monkeypatch):

    class MockBetdb():

        def __init__(self):
            self.fight_table = None
            self.fights = []
            self.bettors_table = None
            self.bettors = {}

        def _db_guard(attr):
            def big_wrap(func):
                def decorator(self, *args, **kwargs):
                    if not getattr(self, attr):
                        raise Exception(f'{attr} not created')
                    return func(self, *args, **kwargs)
                return decorator
            return big_wrap

        def create_fight_table(self):
            self.fight_table = True

        @_db_guard('fight_table')
        def new_fight(self, ftime, first_player, second_player, money1, money2, status, winner):
            self.fights.append([ftime, first_player, second_player,
                                money1, money2, status, winner])
            return ftime.total_seconds()

        @_db_guard('fight_table')
        def record_fight(self, ftime, first_player, second_player,
                         money1=0, money2=0, status='Open', winner=0):
            if len(self.fights) == 0:
                self.fights.append([ftime, first_player, second_player,
                                    money1, money2, status, winner])
            elif self.fights[-1][0] != ftime:
                self.fights.append([ftime, first_player, second_player,
                                    money1, money2, status, winner])
            else:
                self.fights[-1] = [ftime, first_player, second_player,
                                   money1, money2, status, winner]

        @_db_guard('fight_table')
        def get_odds(self, p1, p2):
            for i in reversed(self.fights):
                if i[1] == p1 and i[2] == p2:
                    return ((i[3] / (i[3] + i[4])), (i[4] / (i[3] + i[4])))
            return None, None

        @_db_guard('fight_table')
        def get_money(self, p1, p2):
            for i in reversed(self.fights):
                if i[1] == p1 and i[2] == p2:
                    return i[3], i[4]
            return None, None

        @_db_guard('fight_table')
        def get_winner(self, p1, p2):
            for i in reversed(self.fights):
                if i[1] == p1 and i[2] == p2:
                    return i[6]
            return None

        @_db_guard('fight_table')
        def get_all_fighters(self):
            ret = [(i[1], i[2]) for i in self.fights]
            if ret:
                return set([i for j in ret for i in j])
            return None

        @_db_guard('fight_table')
        def get_all_winners(self):
            ret = {i[i[-1]] for i in self.fights if i[-1] != 0}
            if ret:
                return ret
            return None

        @_db_guard('fight_table')
        def get_all_losers(self):
            ret = {i[(i[-1] % 2) + 1] for i in self.fights if i[-1] != 0}
            if ret:
                return ret
            return None

        @_db_guard('fight_table')
        def get_all_fights(self):
            return self.fights

        @_db_guard('fight_table')
        def get_last_fight(self):
            return self.fights[-1]

        def create_bettor_table(self):
            self.bettors_table = True

        @_db_guard('bettors_table')
        def create_bettor(self, bettor_name, timestamp):
            self.bettors[bettor_name] = []

        @_db_guard('bettors_table')
        def record_bettor(self, bettor_name, ftime, bal, beton=0, wager=0, rank=0):
            if bettor_name not in self.bettors.keys():
                raise Exception(f"{bettor_name} not created.")

            for ind, bet in enumerate(self.bettors[bettor_name]):
                if bet[0] == ftime:
                    self.bettors[bettor_name][ind] = [ftime, bal, beton, wager, rank]
                    return
            self.bettors[bettor_name].append([ftime, bal, beton, wager, rank])

        @_db_guard('bettors_table')
        def record_bettors(self, bettors, fighttime):
            for bettor_name, info in bettors.items():
                if bettor_name not in self.bettors.keys():
                    raise Exception(f"{bettor_name} not created.")
                self.create_bettor(bettor_name, fighttime)
                self.record_bettor(
                    bettor_name, ftime=fighttime, bal=info['balance'],
                    beton=info['bet'], wager=info['wager'], rank=info['rank'])

    # Hacky way of monkeypatching all the attributes without having to write it out
    betdb = MockBetdb()
    for func in [meth for meth in dir(betdb) if
                 not meth.startswith('_') and isinstance(
                     getattr(betdb, meth),
                     type(getattr(betdb, 'create_bettor')))]:
        monkeypatch.setattr(database.Betdb, func, getattr(betdb, func))


"""
    Expected output of parsers given the state put in above
"""


@pytest.fixture
def state_resp_locked_parsed():
    return {
        'first': {'name': "Kris", 'total': "1,603,918"},
        'second': {'name': "Ryu EX3", 'total': "1,863,115"},
        'status': "locked",
        'winner': -1,
        'tournament status': "18 more matches until the next tournament!",
        'time': '',
    }


@pytest.fixture
def state_resp_open_parsed(state_resp_locked_parsed):
    ret = state_resp_locked_parsed
    ret['first']['total'] = '0'
    ret['second']['total'] = '0'
    ret['status'] = 'open'
    return ret


@pytest.fixture
def state_resp_won_parsed(state_resp_locked_parsed):
    ret = state_resp_locked_parsed
    ret['status'] = "2"
    ret['tournament status'] = "17 more matches until the next tournament!"
    return ret


@pytest.fixture
def zdata_resp_parsed(state_resp_locked_parsed):
    return state_resp_locked_parsed


@pytest.fixture
def bettors_parsed(state_resp_locked_parsed):
    return (
        {
            'bettors': {
                "anthraxlol": {
                    'balance': 160596752,
                    'bet': "1",
                    'wager': "150700",
                    'rank': '25',
                    'ranking': "624134",
                },
                "raggedclaws": {
                    'balance': 4541155,
                    'bet': "2",
                    'wager': "6358",
                    'rank': '20',
                    'ranking': "399392",
                },
                "cptodinsbutt": {
                    'balance': 1498,
                    'bet': "2",
                    'wager': "25",
                    'rank': '3',
                    'ranking': "641032",
                },
                "Morphemec": {
                    'balance': 241480,
                    'bet': "2",
                    'wager': "1213",
                    'rank': "17",
                    'ranking': "497924",
                },
                "GuiltyGoob": {
                    'balance': 1948,
                    'bet': "2",
                    'wager': "195",
                    'rank': '4',
                    'ranking': "639735",
                },
                "jimmyfranks": {
                    'balance': 131184,
                    'bet': "2",
                    'wager': "5550",
                    'rank': '25',
                    'ranking': "44991",
                },
                "HateHorror": {
                    'balance': 51892,
                    'bet': "2",
                    'wager': "680",
                    'rank': '19',
                    'ranking': "455375",
                },
            },
            'time': '',
        }, state_resp_locked_parsed)


@pytest.fixture
def bettors_expired_parsed():
    return (
        {
            'bettors': {
                "Justystuff": {
                    'balance': 575,
                    'bet': None,
                    'wager': None,
                    'rank': None,
                    'ranking': "68374",
                },
                "FutaClaws": {
                    'balance': 4612953,
                    'bet': None,
                    'wager': None,
                    'rank': None,
                    'ranking': "588965",
                },

                "Jofahren": {
                    'balance': 3565441,
                    'bet': None,
                    'wager': None,
                    'rank': None,
                    'ranking': "63785",
                },
                "TheRedKirby": {
                    'balance': 14273841,
                    'bet': None,
                    'wager': None,
                    'rank': None,
                    'ranking': "29275",
                },
                "shetaron": {
                    'balance': 2433827,
                    'bet': None,
                    'wager': None,
                    'rank': None,
                    'ranking': "123911",
                },
            },
            'time': '',
        }, {
            'first': {'name': "Ringlerun", 'total': "1,676,717"},
            'second': {'name': "Rolento f. schugerg", 'total': "1,041,053"},
            'status': "2",
            'winner': -1,
            'tournament status': "16 more matches until the next tournament!",
            'time': '',
        })
