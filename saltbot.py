#! /usr/bin/env python3

'''
    Potentially use PhantomJS instead of Chrome webdriver

    TODO: Implement a timer thread, so that the database writes
          arent't counted in addition to the sleeper
'''

import time
import sys
import logging as log
from bs4 import BeautifulSoup as bs

# Python 3.5 compatibility
try:
    from .database import betdb
except ModuleNotFoundError:
    from database import betdb
from selenium.common import exceptions as Except
from selenium import webdriver

log.basicConfig(filename="selenium.log", level=log.DEBUG)


class SaltBot(object):

    auth = False

    def __init__(self, credentials, driver=None):
        self.bet_table = {}
        self.players = []
        self._can_bet = False
        self._base_url = "http://www.saltybet.com/"
        self._auth_url = self._base_url + "authenticate?signin=1"
        self.driver, self.driver_name = self._driver_init(driver)
        if self._authenticate(credentials):
            log.info("Authorized")
            del credentials
        else:
            raise Exception("AuthenticationError")
        self._db = betdb()
        self._db.create_fight_table()

    def _driver_init(self, driver):
        avail = [(webdriver.Chrome, "Chrome"),
                 (webdriver.PhantomJS, "PhantomJS")]
        log.info("Searching for driver")
        if driver is not None:
            driver_name = driver
            driver = avail[[i[1].lower() for i in avail].index(
                driver.lower())][0]()
        else:
            for layer, name in avail:
                try:
                    driver = layer()
                    driver_name = name
                    break
                except Except.WebDriverException:
                    pass
        if driver is None:
            raise Except.WebDriverException
        log.info("Driver {} found".format(driver_name))

        return driver, driver_name

    def _authenticate(self, credentials):
        '''
            Authenticates the user's credentials on the relevant pages of
                saltybets.
                args:
                    driver      -> type == selenium.webdriver
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
        self.driver.get(self._auth_url)
        elem = self.driver.find_element_by_id("email")  # In case nothing is found later
        for item in credentials.keys():
            elem = self.driver.find_element_by_id(item)
            elem.send_keys(credentials[item])
        log.info("Authorization submitted for {}")
        elem.submit()
        if self.driver.current_url != self._base_url and \
                self.driver.current_url == self._auth_url:
            log.info("Authorization failed properly")
            return False
        elif self.driver.current_url != self._base_url:
            log.info("Authorization failed disastrously")
            raise Exception("AuthenticationError: incorrect redirect")
        return True

    def _check_bet(self):
        checker = []
        table = bs(self.driver.page_source, 'html.parser').find('div', id='bet-table')
        for tag in table.find_all('span', class_='submit'):
            checker.append(tag.find('input')['value'])
        self._can_bet = all(checker)

    def update_bettors(self):
        ret = False
        self._check_bet()
        table = bs(self.driver.page_source, 'html.parser').find("div", id="sbettorswrapper")
        if table is not None and not self._can_bet:
            # reset the players
            del self.bet_table
            self.bet_table = {}
            for i, txt in [("1", "redtext"), ("2", "bluetext")]:
                player = table.find('div', id="sbettors" + i).find('span', class_=txt).text
                player = [x.strip() for x in player.split("|")][int(i) - 1]
                if player not in [i[0] for i in self.players]:
                    self.players.append([player, 0, 0])
                    if len(self.players) > 2:
                        self.players.pop(0)
                self.bet_table[player] = []
                for tag in table.find_all('p', class_='bettor-line'):
                    bet = tag.find('span', class_='greentext wager-display')
                    bettor = tag.find('strong')
                    if bet is not None and bettor is not None:
                        bet_val = 0
                        try:
                            if 'K' in bet.text:
                                bet_val = int(float(bet.text.strip()[1:-1]) * 1000)
                            else:
                                if bet.text:
                                    bet_val = int(bet.text.strip()[1:].replace(",", ""))
                        except ValueError:
                            print("Error on conversion {} {}".format(bet.text, bettor.text))
                        self.bet_table[player].append({'bet': bet_val, 'bettor': bettor.text})
            ret = True
        return ret

    def update_players(self):
        ret = False
        self._check_bet()
        if self._can_bet:
            table = bs(self.driver.page_source, 'html.parser').find('div', id='bet-table')
            for tag in table.find_all('span', class_='submit'):
                player = tag.find('input')['value']
                if player not in [i[0] for i in self.players] and player:
                    self.players.append([player, 0, 0])
                    if len(self.players) > 2:
                        self.players.pop(0)
            ret = True
        return ret

    def update_money(self):
        dollar = bs(self.driver.page_source, 'html.parser').find("span", class_="dollar", id="balance")
        return int(dollar.text) if dollar is not None else 0

    def update_bets_for(self):
        ret = False
        bet_tag = bs(self.driver.page_source, 'html.parser').find("span", id="odds")
        if bet_tag.find("span", class_="redtext") is not None:
            b_for = {}
            for team in bet_tag.text.split("\xa0\xa0"):
                b_for[" ".join(team.split(" ")[:-1]).strip()] = int(
                    team.split(" ")[-1].strip(" $").replace(",", ""))
            for player, money in b_for.items():
                if player in [i[0] for i in self.players]:
                    self.players[[i[0] for i in self.players].index(player)][2] = money
            ret = True
        return ret

    def update_odds(self):
        ret = False
        bet_tag = bs(self.driver.page_source, 'html.parser').find("span", id="lastbet")
        if bet_tag.find("span", class_="redtext") is not None:
            bet_odds = [bet_tag.find("span", class_="redtext").text]
            bet_odds.append(bet_tag.find("span", class_="bluetext").text)

            try:
                bet_odds = list(map(float, bet_odds))
            except ValueError:
                bet_odds = [0, 0]

            self.players[0][1] = bet_odds[0]
            self.players[1][1] = bet_odds[1]
            ret = True
        return ret

    def bet(self, amount, player):
        assert(player == "player1" or player == "player2")
        sent = False
        source = bs(self.driver.page_source, 'html.parser')
        if "none" in source.find("input", placeholder="Wager")['style'] and False:  # Betting disabled while testing
            elem = self.driver.find_element_by_id("wager")
            choice = self.driver.find_element_by_id(player)
            elem.send_keys(str(amount))
            choice.submit()
            sent = True
        return sent

    def record(self):
        updates = [self.update_bettors, self.update_players,
                   self.update_money, self.update_bets_for,
                   self.update_odds]
        try:
            old_players = []
            update_arr = {z.__name__: False for z in updates}
            fight_time = None
            while True:
                print("Players: {}".format(
                    ", ".join(["(" + ", ".join(map(str, i)) + ")" for i in self.players])))
                for i in updates:
                    update_arr[i.__name__] = i()

                print("Updated members:\n{}".format(" ".join(
                    ["{}: {}".format(i, j) for i, j in update_arr.items()])))

                print("Checking database writes")

                if not all(map(lambda x: x[0] == x[1], zip(old_players, self.players))):
                    fight_time = self._db.new_fight(self.players[0][0], self.players[1][0],
                                                    self.players[0][1], self.players[1][1],
                                                    self.players[0][2], self.playerse[2][2])
                    print("New players")
                    if self.bet_table and all(map(
                            lambda x: x in self.players,
                            self.bet_table.keys())) and all(self.bet_table.values()):
                        self._db.insert_bettors(
                            self.players[0][0], self.players[1][0],
                            fight_time, self.bet_table)

                    print("New players written")
                else:
                    if all(map(lambda x: x[1] != 0, self.players)):
                        self._db.update_odds(self.players[0][0], self.players[1][0],
                                             self.players[0][1], self.players[1][1])
                        print("Updated odds")
                    if all(map(lambda x: x[2] != 0, self.players)):
                        self._db.update_money(self.players[0][0], self.players[1][0],
                                              self.players[0][2], self.players[1][2])
                        print("Updated money")
                    if self.bet_table and all(map(
                            lambda x: x in self.players,
                            self.bet_table.values())) and all(self.bet_table.values()):
                        if not self._db.bet_table_empty(self.players[0][0],
                                                        self.players[0][1],
                                                        fight_time):
                            self._db.insert_bettors(
                                self.players[0][0], self.players[1][0],
                                fight_time, self.bet_table)
                        print("Updated bet table")
                old_players = self.players
                time.sleep(10)

        except KeyboardInterrupt:
            print("Cleaning up")

    def run(self):
        try:
            while True:
                for func in [self.update_bettors, self.update_players,
                             self.update_money, self.update_bets_for,
                             self.update_odds]:
                    print("Running {}".format(func.__name__))
                    print("Successful") if func() else print("Failed")
                    print(self.players)
                time.sleep(5)
        except KeyboardInterrupt:
            print("Cleaning up")


# This is for preliminary testing, change in the future
def get_credentials():
    '''
        Returns the credentials of the user, whether stored somewhere
            on the machine or entered by hand.

        returns
            credentials -> type == dictionary
    '''
    email = input("email: ")
    passwd = input("password: ")
    return {"email": email, "pword": passwd}


def main(email=None, pwrd=None):
    drive = input("Specific driver? ")
    if drive == "no":
        drive = None
    salt_bot = SaltBot(get_credentials(), driver=drive)
    salt_bot.record()


if __name__ == "__main__":
    try:
        main(email=sys.argv[1], pwrd=sys.argv[2])
    except IndexError:
        main()
