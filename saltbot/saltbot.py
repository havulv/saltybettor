#! /usr/bin/env python

'''
    TODO: Implement a timer thread, so that the database writes
          arent't counted in addition to the sleeper
'''
from selenium.common import exceptions as selenium_except
from selenium import webdriver
import logging as log
import requests
import argparse
import time
import sys
import re
import os

try:
    from .database import Betdb, digit_map
except ImportError:
    from database import Betdb, digit_map

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

    def __init__(self, driver=None,
                 creds=None,
                 chrome_headless=None):
        self._base_url = "http://www.saltybet.com/"
        self.logged_in = False
        if creds and driver:
            self.driver, self.driver_name = self._driver_init(driver,
                                                              chrome_headless)
            self._authenticate(creds)
            if self.logged_in:
                root.info("Authorized")
                del creds
            else:
                raise Exception("AuthenticationError")
            # At some point I need to grab the cookies from the login or something
            self.driver.close()

        self.db = Betdb()
        self.db.create_fight_table()
        self.db.create_bettor_table()
        root.info("Database loaded into memory")
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
        email = self.driver.find_element_by_id("email")
        email.send_keys(credentials['email'])

        password = self.driver.find_element_by_id("password")
        password.send_keys(credentials['password'])
        password.submit()

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

    def get_match(self, write=True, fighttime=None):
        '''
            Get the match -- write auto updates // writes the match to the
            database to simplify calls
        '''
        match_time = int(time.time())
        req = requests.get(self._base_url + 'state.json',
                           params={'t': match_time})
        if req.status_code != 200:
            raise Exception('requests error')

        bet_json = req.json()
        fight_status = self.parse_match(bet_json, match_time)
        ftime = fight_status['time'] if fighttime is None else fighttime

        self.db.record_fight(
            ftime,
            fight_status['first']['name'],
            fight_status['second']['name'],
            int(fight_status['first']['total'].replace(',', '')),
            int(fight_status['second']['total'].replace(',', '')),
            fight_status['status'],
            int(fight_status['winner']))

        return fight_status

    def parse_match(self, bet_json, match_time):
        winner = -1
        status = bet_json['status']
        if status not in ['open', 'locked']:
            status = 'over'
            winner = bet_json['status']

        return {'first': {'name': bet_json['p1name'], 'total': bet_json['p1total']},
                'second': {'name': bet_json['p2name'], 'total': bet_json['p2total']},
                'status': status,
                'winner': winner,
                'tournament status': bet_json['remaining'],
                'time': match_time}

    def get_bettors(self, fighttime=None):
        match_time = int(time.time())
        req = requests.get(self._base_url + 'zdata.json',
                           params={'t': match_time})

        if req.status_code != 200:
            raise Exception('requests error')

        bettor_json = req.json()
        bettor_data = {k: v for k, v in bettor_json.items() if k.isdigit()}
        match_data = {k: v for k, v in bettor_json.items() if not k.isdigit()}

        match = self.parse_match(match_data, match_time)
        bettors = {}
        for ind, values in bettor_data.items():
            name = values['n']
            if name[0].isdigit():
                name = digit_map[int(name[0])] + name[1:]
            bettors[name] = {'balance': int(values.get('b').replace(',', ''))}
            bettors[name]['bet'] = values.get('p')
            bettors[name]['wager'] = values.get('w')
            bettors[name]['rank'] = values.get('r')
            if bettors[name]['rank'] is not None:
                if len(bettors[name]['rank']) > 2:
                    bettors[name]['rank'] = 25

        ftime = match['time'] if fighttime is None else fighttime
        self.db.record_fight(
            ftime,
            match['first']['name'],
            match['second']['name'],
            int(match['first']['total'].replace(',', '')),
            int(match['second']['total'].replace(',', '')),
            match['status'],
            int(match['winner']))

        self.db.record_bettors(
            bettors,
            ftime)

        return ({'bettors': bettors, 'time': ftime}, match)

    def fight_status(self, fighttime=None):
        fight_status = self.get_match(fighttime=fighttime)
        ftime = fight_status['time'] if fighttime is None else fighttime

        return ftime, fight_status

    def bettor_status(self, fighttime=None):
        bettor_status, fight_status = self.get_bettors(fighttime)
        ftime = fight_status['time'] if fighttime is None else fighttime
        return ftime, fight_status

    def run(self):
        ftime = None
        last_won = {'first': {'name': None, 'total': None},
                    'second': {'name': None, 'total': None},
                    'winner': -1}
        try:
            while True:
                ftime, fght = self.fight_status(ftime)
                if fght['first']['name'] != last_won['first']['name'] and fght['second']['name'] != last_won['second']['name'] and last_won['winner'] != -1:
                    ftime = None
                    ftime, fght = self.fight_status(ftime)
                    last_won['winner'] = -1
                time.sleep(2)
                if fght['status'] not in ['open', 'over']:
                    ftime, fght = self.bettor_status(ftime)
                    print(ftime, f"| {fght['first']['name']} ({fght['first']['total']}) vs. {fght['second']['name']} ({fght['second']['total']})", end="\r")

                print(ftime, f"- {fght['first']['name']} ({fght['first']['total']}) vs. {fght['second']['name']} ({fght['second']['total']})", end="\r")
                if int(fght['winner']) > -1:
                    if last_won['first']['name'] != fght['first']['name'] and last_won['second']['name'] != fght['second']['name']:
                        print(' ' * os.get_terminal_size()[0], end='\r')
                        print(f"{fght['first' if fght['winner'] == 0 else 'second']} won!")
                        last_won['first'] = fght['first']
                        last_won['second'] = fght['second']
                        last_won['winner'] = fght['winner']

        except KeyboardInterrupt:
            root.info("Keyboard close")
            print("Cleaning up")


def main(args):
    creds = None
    if args.email and args.password:
        creds = {'email': args.email,
                 'password': args.password}
    salt_bot = SaltBot(
        creds=creds,
        driver=args.driver)

    salt_bot.run()


def parse_email(addr):

    if isinstance(addr, str):
        if re.fullmatch(r"[^@]+@[^@]+\.[^@]+", addr) or addr is None:
            return addr

    raise argparse.ArgumentTypeError(
        f"{addr} is not a valid email address.")


def parse_args(args):

    parser = argparse.ArgumentParser(
        prog='saltybettor',
        description='A bot for placing bets on SaltyBet, running'
                    ' off of selenium and the Gmail API (email alerts).')
    parser.add_argument(
        '-e', '--email', type=parse_email, default=None,
        help=("A gmail address for alerts on the bot."))
    parser.add_argument(
        '-p', '--password', nargs=1, default=None,
        help=("The password for the email that is being used."))
    parser.add_argument(
        '-d', '--driver', nargs=1, type=str, default=None,
        help=("The path to the driver(s) to use for the bot."))

    return parser.parse_args(args)


if __name__ == "__main__":
    main(parse_args(sys.argv[1:]))
