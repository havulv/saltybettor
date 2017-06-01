#! /usr/bin/env python3

'''
    Potentially use PhantomJS instead of Chrome webdriver

    TODO: Implement a timer thread, so that the database writes
          arent't counted in addition to the sleeper
'''

import time
import logging as log
from datetime import datetime as dt
from bs4 import BeautifulSoup as bs
from database import betdb
from selenium import webdriver
from selenium.common import exceptions as Except

log.basicConfig(filename="saltbot.log", level=log.INFO,
                format="%(asctime)s [%(levelname)s] :: %(message)s")


def l_strcmp(str1, str2):
    end = len(str1) if len(str1) < len(str2) else len(str2)
    for i, j in zip(str1[:end], str2[:end]):
        if i != j:
            return False
    return True


def keyboardwrap(func):
    def wrapper(*args, **kwargs):
        ret = None
        try:
            ret = func(*args, **kwargs)
        except KeyboardInterrupt:
            log.info("Keyboard quit out")
            print("Cleaning up")
        return ret
    return wrapper


class SaltBot(object):

    auth = False

    def __init__(self, credentials, driver=None):
        self.prev_winner = None
        self.bet_table = {}
        self.players = [[None, 0, 0], [None, 0, 0]]
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
        self.odds_dict = {}
        self.win_dict = {}
        self.avg_odds_dict = {}
        self.fighters = []

    def _driver_init(self, driver):
        avail = [(webdriver.Chrome, "Chrome"),
                 (webdriver.PhantomJS, "PhantomJS")]
        log.info("Searching for driver")
        if driver is not None:
            driver_set = list(map(lambda x: x.lower().strip(),
                                  driver.split(' ')))
            if len(driver_set) < 2:
                driver_name = driver_set[0]
                driver = avail[[i[1].lower() for i in avail].index(
                    driver.lower())][0]()
            else:
                # If using chrome headless then the input is [chrome, headless, path]
                if 'headless' in driver_set and "chrome" in driver_set:
                    options = webdriver.ChromeOptions()
                    options.binary_location = driver_set[2]
                    options.add_argument('headless')
                    driver = webdriver.Chrome(chrome_options=options)

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
        log.info(
            "Authorization submitted for {}".format(credentials['email']))
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
        table = bs(self.driver.page_source,
                   'html.parser').find('div', id='bet-table')
        for tag in table.find_all('span', class_='submit'):
            checker.append(tag.find('input')['value'])
        self._can_bet = all(checker)

    # The winner tag is only available for about 4-5 seconds, so timeouts that check this
    # value should remain in the 2-2.5 second zone so they don't miss the win.
    def update_winner(self):
        ret = False
        status = bs(self.driver.page_source,
                    'html.parser').find("span", id="betstatus")
        if status is not None:
            status = status.text
            if "wins" in status:
                winner = status.split(" ")
                self.winner = " ".join(winner[:winner.index("wins!")])
                ret = True
            else:
                self.winner = None
        return ret

    def update_bettors(self):
        ret = False
        self._check_bet()
        table = bs(self.driver.page_source,
                   'html.parser').find("div", id="sbettorswrapper")
        if table is not None and not self._can_bet:
            # reset the players
            del self.bet_table
            self.bet_table = {}
            for i, txt in [("1", "redtext"), ("2", "bluetext")]:
                player = table.find(
                    'div', id="sbettors" + i).find('span', class_=txt)
                if player is not None:
                    player = player.text
                    try:
                        player = [x.strip() for x in player.split("|")][int(i) - 1]
                    except IndexError:
                        print(player)
                        print([x.strip() for x in player.split("|")])
                        print(int(i) - 1)
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
                                elif 'M' in bet.text:
                                    bet_val = int(float(bet.text.strip()[1:-1]) * 1000000)
                                else:
                                    if bet.text:
                                        bet_val = int(bet.text.strip()[1:].replace(",", ""))
                            except ValueError:
                                log.info("Error on conversion {} {}".format(bet.text, bettor.text))
                            self.bet_table[player].append({'bet': bet_val, 'bettor': bettor.text})
            ret = True
        return ret

    def update_players(self):
        ret = False
        self._check_bet()
        if self._can_bet:
            table = bs(self.driver.page_source,
                       'html.parser').find('div', id='bet-table')
            for tag in table.find_all('span', class_='submit'):
                player = tag.find('input')['value']
                if player not in [i[0] for i in self.players] and player:
                    self.players.append([player, 0, 0])
                    if len(self.players) > 2:
                        self.players.pop(0)
            ret = True
        return ret

    def update_money(self):
        dollar = bs(self.driver.page_source,
                    'html.parser').find(
                        "span", class_="dollar", id="balance")
        if dollar is not None:
            dollar = int(dollar.text.replace(",", ""))
        else:
            dollar = 0
        return dollar

    def update_bets_for(self):
        ret = False
        bet_tag = bs(self.driver.page_source,
                     'html.parser').find("span", id="odds")
        if bet_tag.find("span", class_="redtext") is not None:
            b_for = {}
            for team in bet_tag.text.split("\xa0\xa0"):
                b_for[" ".join(team.split(" ")[:-1]).strip()] = int(
                    team.split(" ")[-1].strip(" $").replace(",", ""))
            for player, money in b_for.items():
                if player in [i[0] for i in self.players]:
                    self.players[
                        [i[0] for i in self.players].index(
                            player)][2] = money
            ret = True
        return ret

    def update_odds(self):
        ret = False
        bet_tag = bs(self.driver.page_source,
                     'html.parser').find("span", id="lastbet")
        if bet_tag.find("span", class_="redtext") is not None:
            bet_odds = [bet_tag.find("span",
                                     class_="redtext").text]
            bet_odds.append(bet_tag.find("span",
                                         class_="bluetext").text)

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
        if "none" in source.find("input", placeholder="Wager")['style'] and False:  # Betting disabled while testing (i.e. false)
            elem = self.driver.find_element_by_id("wager")
            choice = self.driver.find_element_by_id(player)
            elem.send_keys(str(amount))
            choice.submit()
            sent = True
        return sent

    def load(self):
        success = False
        fights = self._db.get_all_fights()
        if fights is not None:
            self.fighters = list(set(
                [k for j in [(i[0], i[1]) for i in fights] for k in j]))

            self.odds_dict = {fighter: {} for fighter in self.fighters}
            self.win_dict = {fighter: {} for fighter in self.fighters}
            self.fight_dict = {fighter: 0 for fighter in self.fighters}
            self.avg_odds_dict = {fighter: 0 for fighter in self.fighters}

            while len(fights) > 0:
                t1, t2, o1, o2, win = fights.pop()
                loser = t1 if win == t2 else t2
                self.fight_dict[loser] += 1
                self.fight_dict[win] += 1
                for i, j in zip([self.win_dict, self.odds_dict, self.odds_dict],
                                [(win, loser, 1), (t1, t2, o1), (t2, t1, o2)]):
                    if i[j[0]].get(j[1]) is not None:
                        i[j[0]][j[1]] += j[2]
                    else:
                        i[j[0]][j[1]] = j[2]

            # Compute average odds
            for fighter in self.fighters:
                self.avg_odds_dict[fighter] = sum(self.odds_dict[fighter].values()) / self.fight_dict[fighter]

            success = True
        return success

    def get_wins(self, player1, player2):
        return (sum(self.win_dict[player1].values)
                if self.win_dict.get(player1) is not None else None,
                sum(self.win_dict[player2].values)
                if self.win_dict.get(player2) is not None else None)

    def get_cumm_odds(self, player1, player2):
        return (sum(self.odds_dict[player1].values)
                if self.odds_dict.get(player1) is not None else None,
                sum(self.odds_dict[player2].values)
                if self.odds_dict.get(player2) is not None else None)

    def get_avg_odds(self, player1, player2):
        return (sum(self.avg_odds_dict[player1].values)
                if self.avg_odds_dict.get(player1) is not None else None,
                sum(self.avg_odds_dict[player2].values)
                if self.avg_odds_dict.get(player2) is not None else None)

    def append_fighters(self, player):
        if player not in self.fighters:
            self.fighters.append(player)

        for i, j in zip([self.fight_dict, self.odds_dict, self.avg_odds_dict],
                        [0, {}, 0]):
            if i.get(player) is None:
                i[player] = j
            else:
                if j != {}:
                    i[player] += j

    def create_fight(self):
        fight_time = self._db.new_fight(self.players[0][0],
                                        self.players[1][0])
        log.info("New players: {}".format(
            " vs. ".join([i[0] for i in self.players])))

        self.append_fighters(self.players[0][0])
        self.append_fighters(self.players[1][0])

        self.fight_dict[self.players[0][0]] += 1
        self.fight_dict[self.players[1][0]] += 1

        if self.bet_table and all(map(lambda x: x in self.players,
                                      self.bet_table.keys())):
            self._db.insert_bettors(
                self.players[0][0], self.players[1][0],
                fight_time, self.bet_table)

        return fight_time

    def create_odds(self, fight_time):
        db_odds = self._db.get_odds(self.players[0][0],
                                    self.players[1][0])

        if all([self.players[i][1] != db_odds[i] for i
                in range(len(self.players))]):

            self._db.update_odds(self.players[0][0], self.players[1][0],
                                 self.players[0][1], self.players[1][1],
                                 fight_time)

            if self.odds_dict.get(self.players[0][0]) is None:
                self.odds_dict[self.players[0][0]] = {self.players[1][0]: self.players[1][1]}
            else:
                self.odds_dict[self.players[0][0]][self.players[1][0]] += self.players[0][1]

            if self.odds_dict.get(self.players[1][0]) is None:
                self.odds_dict[self.players[1][0]] = {self.players[0][0]: self.players[0][1]}
            else:
                self.odds_dict[self.players[1][0]][self.players[0][1]] += self.players[1][1]

            log.info("Updated odds: {} ({}) vs. {} ({})".format(
                self.players[0][0], self.players[0][1],
                self.players[1][0], self.players[1][1]))

    def create_money(self, fight_time):
        db_money = self._db.get_money(self.players[0][0],
                                      self.players[1][0])

        if all([self.players[i][2] != db_money[i] for i
                in range(len(self.players))]):
            self._db.update_money(self.players[0][0], self.players[1][0],
                                  self.players[0][2], self.players[1][2],
                                  fight_time)

            log.info("Updated money: {} (${:,}) vs. {} (${:,})".format(
                self.players[0][0], self.players[0][2],
                self.players[1][0], self.players[1][2]))

    def create_winner(self, fight_time):
        self._db.update_winner(self.players[0][0], self.players[1][0],
                               fight_time, self.winner)

        if l_strcmp(self.winner, self.players[1][0]):
            if self.win_dict[self.players[1][0]].get([self.players[0][0]]) is None:
                self.win_dict[self.players[1][0]][self.players[0][0]] = 1
            else:
                self.win_dict[self.players[1][0]][self.players[0][0]] += 1
        else:
            if self.win_dict[self.players[0][0]].get([self.players[1][0]]) is None:
                self.win_dict[self.players[0][0]][self.players[1][0]] = 1
            else:
                self.win_dict[self.players[0][0]][self.players[1][0]] += 1

        log.info("Updated winner: {}".format(self.winner))

    def create_bet_table(self, fight_time):
        if not self._db.bet_table_empty(self.players[0][0],
                                        self.players[1][0],
                                        fight_time):
            self._db.insert_bettors(
                self.players[0][0], self.players[1][0],
                fight_time, self.bet_table)

        log.info("Updated bet table, fight_{}_{}_{}".format(
            self.players[0][0], self.players[1][0],
            dt.strftime(fight_time, '%m_%d_%Y_%M')))

    def _validate_players(self, old_players, fight_time):
        if all(map(lambda x: x is not None, [i[0] for i in self.players])):
            try:
                int(self.players[0][0])
                int(self.players[1][0])
                old_players = [None, None]
                self.players[0][0] = None
                self.players[1][0] = None
                fight_time = None
            except ValueError:
                pass
        return old_players, fight_time

    @keyboardwrap
    def record(self):
        updates = [self.update_bettors, self.update_players,
                   self.update_money, self.update_bets_for,
                   self.update_odds, self.update_winner]
        old_players = [None, None]
        update_arr = {z.__name__: False for z in updates}
        fight_time = None

        while True:
            log.debug("Players: {}".format(
                ", ".join(["(" + ", ".join(map(str, i)) + ")" for i
                           in self.players])))
            for i in updates:
                update_arr[i.__name__] = i()

            log.debug("Updated members: {}".format(" ".join(
                ["{}: {}".format(i, j) for i, j
                 in update_arr.items()])))

            log.debug("Fight Time: {}".format(
                "None" if fight_time is None
                else dt.strftime(fight_time, '%m_%d_%Y_%M')))

            log.debug("Checking database writes")
            old_players, fight_time = self._validate_players(
                old_players, fight_time)

            if all(map(lambda x: old_players[x] != self.players[x][0],
                       range(2))):
                fight_time = self.create_fight()
            else:
                if fight_time is not None and \
                        all(map(lambda x: x[1] != 0,
                                self.players)):
                    self.create_odds(fight_time)

                if fight_time is not None and \
                        all(map(lambda x: x[2] != 0,
                                self.players)):
                    self.create_money(fight_time)

                if self.bet_table and \
                        all(map(lambda x: x in self.players,
                                self.bet_table.keys())):
                    self.create_bet_table(fight_time)

                if self.winner is not None:
                    self.create_winner(fight_time)

            old_players = [self.players[0][0], self.players[1][0]]
            time.sleep(4.75)

    def run(self):
        try:
            while True:
                for func in [self.update_bettors, self.update_players,
                             self.update_money, self.update_bets_for,
                             self.update_odds, self.update_winner]:
                    log.info("Running {}".format(func.__name__))
                    log.info("Successful" if func() else "Failed")
                    log.debug(self.players)
                time.sleep(3)
        except KeyboardInterrupt:
            log.info("Keyboard close")
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

    if salt_bot.load():
        print("Database loaded into memory")
        log.info("Database loaded into memory")

    salt_bot.record()


if __name__ == "__main__":
    import sys
    try:
        main(email=sys.argv[1], pwrd=sys.argv[2])
    except IndexError:
        main()
