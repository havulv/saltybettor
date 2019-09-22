#! /usr/bin/python3.7


'''
    Tests should cover:
        * Proper application logic
        * Information is being properly processed and validated
        * Minimal side effects and seperation of concerns are preserved
'''

from saltbot.saltbot import SaltBot
import pytest
import time


def test_get_home(silent_requests, site_cookies):
    bot = SaltBot(dbname='testing')
    bot.get('https://www.saltybet.com')
    assert bot.session.cookies == site_cookies


def test_get_state(silent_requests, state_resp_open):
    bot = SaltBot(dbname='testing')
    resp = bot.get(
        'https://www.saltybet.com/state.json',
        params={'t': int(time.time())})
    assert resp.json() == state_resp_open


def test_get_zdata(silent_requests, zdata_resp):
    bot = SaltBot(dbname='testing')
    resp = bot.get(
        'https://www.saltybet.com/zdata.json',
        params={'t': int(time.time())})
    assert resp.json() == zdata_resp


def test_get_bad_state(silent_requests):
    with pytest.raises(Exception):
        bot = SaltBot(dbname='testing')
        bot.get('https://www.saltybet.com/state.json')


def test_get_bad_zdata(silent_requests):
    with pytest.raises(Exception):
        bot = SaltBot(dbname='testing')
        bot.get('https://www.saltybet.com/zdata.json')


def test_run(silent_requests, silent_database):
    bot = SaltBot(dbname='testing')
    bot.run(number=1)
    assert bot.db.get_last_fight() is not None


def test_get_match(silent_requests, silent_database):
    bot = SaltBot(dbname='testing')
    bot.get_match()
    assert bot.db.get_last_fight() is not None


def test_parse_match(silent_requests, silent_database,
                     state_resp_open_parsed):
    bot = SaltBot(dbname='testing')
    ftime = time.time()
    state_resp_open_parsed['time'] = ftime
    resp = bot.get(
        'https://www.saltybet.com/zdata.json',
        params={'t': int(ftime)})
    fight = bot.parse_match(resp.json(), ftime)
    assert fight == state_resp_open_parsed


def test_get_bettors(silent_requests, silent_database):
    bot = SaltBot(dbname='testing')
    pass


def test_fight_status(silent_requests, silent_database):
    bot = SaltBot(dbname='testing')
    pass


def test_bettor_status(silent_requests, silent_database):
    bot = SaltBot(dbname='testing')
    pass
