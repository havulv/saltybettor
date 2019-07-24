#! /usr/bin/env python

'''
    TODO: Implement a timer thread, so that the database writes
          arent't counted in addition to the sleeper
'''

from selenium.common import exceptions as selenium_except
from selenium import webdriver
from .database import Betdb
import logging as log
import requests
import argparse
import time
import sys
import re
import os


log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs"))
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

root = log.getLogger(name='root')
root.setLevel(log.DEBUG)
fhandler = log.FileHandler(os.path.join(log_dir, 'saltbot.log'))
fhandler.setLevel(log.DEBUG)
formatter = log.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler.setFormatter(formatter)
root.addHandler(fhandler)


def l_strcmp(str1, str2):
    ''' A loose string comparison for checking two grepped strings '''
    end = len(str1) if len(str1) < len(str2) else len(str2)
    for i, j in zip(str1[:end], str2[:end]):
        if i != j:
            return False
    return True


def keyboardwrap(func):
    ''' Wrapper for quit out by Ctrl-C '''
    def wrapper(*args, **kwargs):
        ret = None
        try:
            ret = func(*args, **kwargs)
        except KeyboardInterrupt:
            root.info("Keyboard quit out")
            print("Cleaning up")
        return ret
    return wrapper


class SaltBot(object):
    '''
        The main SaltBot which controls the database writes and holds
        data structures pertaining to the performance of individual
        characters.
    '''

    auth = False

    def __init__(self, name, driver,
                 creds=None,
                 chrome_headless=None):
        self._base_url = "http://www.saltybet.com/"
        self.logged_in = False
        self.driver, self.driver_name = self._driver_init(name,
                                                          chrome_headless)
        if creds is not None:
            self._authenticate(creds)
            if self.logged_in:
                root.info("Authorized")
                del creds
            else:
                raise Exception("AuthenticationError")

        self.db = Betdb()
        self.db.create_fight_table()
        self.odds_dict = {}
        self.win_dict = {}
        self.avg_odds_dict = {}
        self.fighters = []

    def _driver_init(self, name, chrome_headless=None):
        '''
            Private method for initializing a chosen driver.
                Supports Chrome and Firefox and handles some
                of the errors associated with driver initialization.
                Headless chrome requires that you input the path to
                the chrome binary. If None is passed as an argument,
                then the function will search for the first available
                webdriver in the $PATH variable.

            Returns the driver that is being used and the name of
                said driver.

            args:
                name            -> type    == str or None
                                   accepts == chrome, firefox, gecko
                chrome_headless -> type == filepath
            returns:
                driver          -> type == selenium.webdriver
                driver_name     -> type == str
        '''
        driver = None
        avail = {'chrome': webdriver.Chrome,
                 'firefox': webdriver.Firefox}
        root.info("Searching for driver")
        if 'chrome' in name.lower() and chrome_headless is not None:
            # If using chrome headless then the input is [chrome, headless, path]
            options = webdriver.ChromeOptions()
            pth = os.path.normpath(chrome_headless)
            options.binary_location = pth
            options.add_argument('headless')
            driver = webdriver.Chrome(chrome_options=options)
            driver_name = "headless chrome"
        elif 'firefox' in name.lower() or 'gecko' in name.lower():
            driver = webdriver.Firefox()
            driver_name = 'firefox'
        else:
            for name, layer in avail.items():
                try:
                    driver = layer()
                    driver_name = name
                    break
                except selenium_except.WebDriverException:
                    pass
        if driver is None:
            raise selenium_except.WebDriverException
        root.info("Driver {} found".format(driver_name))

        return driver, driver_name

    def _authenticate(self, credentials):
        '''
            Authenticates the user's credentials on the relevant pages of
                saltybets.

            args:
                credentials -> type == dictionary
            returns:
                bool

            I really hate that this is a function because it has huge side effects
                It changes the ENTIRE state of the browser. But this can't be
                avoided because the web is stateful. Damn web
            In the end, the IO has to be somewhere so at least it is all in one
                place and then only changes one item of global state
                i.e. site -> authenticate -> site (authenticated)
        '''
        auth_url = self._base_url + "authenticate?signin=1"
        self.driver.get(auth_url)
        elem = self.driver.find_element_by_id("email")  # In case nothing is found later
        for item in credentials.keys():
            elem = self.driver.find_element_by_id(item)
            elem.send_keys(credentials[item])
        elem.submit()
        root.info(
            "Authorization submitted for {}".format(credentials['email']))
        if self.driver.current_url != self._base_url and \
                self.driver.current_url == auth_url:
            root.info("Authorization failed properly")
            return
        elif self.driver.current_url != self._base_url:
            root.info("Authorization failed disastrously")
            raise Exception("AuthenticationError: incorrect redirect")
        self.logged_in = True

    def get_match(self):
        match_time = int(time.time())
        req = requests.get(self.base_url + 'state.json',
                           params={'t': match_time})
        if req.status_code != 200:
            raise Exception('requests error')

        bet_json = req.json()
        return self.parse_match(bet_json, match_time)

    def parse_match(self, bet_json, match_time):
        winner = None
        status = bet_json['status']
        if status not in ['open', 'locked']:
            status = 'over'
            winner = bet_json['status']

        return {'first': {'name': bet_json['p1name'], 'total': bet_json['p1total']},
                'second': {'name': bet_json['p2name'], 'total': bet_json['p2total']},
                'bet status': status,
                'winner': winner,
                'tournament status': bet_json['remaining'],
                'time': match_time}

    def get_bettors(self):
        match_time = int(time.time())
        req = requests.get(self.base_url + 'zdata.json',
                           params={'t': match_time})

        if req.status_code != 200:
            raise Exception('requests error')

        bettor_json = req.json()
        bettor_data = {k: v for k, v in bettor_json.items() if k.isdigit()}
        match_data = {k: v for k, v in bettor_json.items() if not k.isdigit()}

        bettors = {}
        for ind, values in bettor_data:
            name = values['n']
            bettors[name] = {'balance': int(values.get('b'))}
            bettors[name]['bet'] = values.get('p')
            bettors[name]['wager'] = values.get('w')
            bettors[name]['rank'] = values.get('r')
            if bettors[name]['rank'] is not None:
                if len(bettors[name]['rank']) > 2:
                    bettors[name]['rank'] = 25

        return ({'bettors': bettors, 'time': time},
                self.parse_match(match_data, match_time))

    def fight_status(self, fighttime=None):
        fight_status = self.get_match()
        ftime = fight_status['time'] if fighttime is None else fighttime
        self.db.record_fight(
            ftime,
            fight_status['first']['name'],
            int(fight_status['first']['total']),
            fight_status['second']['name'],
            int(fight_status['second']['total']),
            fight_status['status'],
            int(fight_status['winner']))

        return ftime, fight_status['winner']

    def bettor_status(self, fighttime=None):
        bettor_status, fight_status = self.get_bettors()
        ftime = fight_status['time'] if fighttime is None else fighttime
        self.db.record_fight(
            ftime,
            fight_status['first']['name'],
            int(fight_status['first']['total']),
            fight_status['second']['name'],
            int(fight_status['second']['total']),
            fight_status['status'],
            int(fight_status['winner']))

        self.db.record_bettors(
            bettor_status['bettors'],
            ftime)
        return ftime, fight_status['winner']

    def run(self):
        ftime = None
        try:
            while True:
                ftime, won = self.fight_status(self, ftime)
                time.sleep(3)
                ftime, won = self.bettor_status(self, ftime)
                if won is not None:
                    ftime = None
                time.sleep(5)
        except KeyboardInterrupt:
            root.info("Keyboard close")
            print("Cleaning up")


# This is for preliminary testing, change in the future
def get_credentials(email, passwd):
    '''
        Returns the credentials of the user, whether stored somewhere
            on the machine or entered by hand.

        returns
            credentials -> type == dictionary
    '''
    if not email:
        email = input("email: ")

    if not passwd:
        passwd = input("password: ")
    return {"email": email, "pword": passwd}


def main(args):
    salt_bot = SaltBot(
        get_credentials(args.email, args.password),
        driver=args.driver,
        chrome_headless=args.headless)

    if salt_bot.load():
        print("Database loaded into memory")
        root.info("Database loaded into memory")

    salt_bot.record()


def parse_email(addr):

    if isinstance(addr, str):
        if re.fullmatch(r"[^@]+@[^@]+\.[^@]+", addr):
            return addr

    raise argparse.ArgumentTypeError(
        f"{addr} is not a valid email address.")


def parse_args(args):

    parser = argparse.ArgumentParser(
        prog='saltybettor',
        description='A bot for placing bets on SaltyBet, running'
                    ' off of selenium and the Gmail API (email alerts).')
    parser.add_argument(
        '-e', '--email', type=parse_email,
        help=("A gmail address for alerts on the bot."))
    parser.add_argument(
        '-p', '--password', nargs=1,
        help=("The password for the email that is being used."))
    parser.add_argument(
        '-d', '--driver', nargs=1, type=str,
        help=("The path to the driver(s) to use for the bot."))

    return parser.parse_args(args)


if __name__ == "__main__":
    main(parse_args(sys.argv[1:]))
