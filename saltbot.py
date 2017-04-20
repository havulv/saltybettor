#! /usr/bin/env python3

''' Potentially use PhantomJS instead of Chrome webdriver '''

import time
import sys
import logging as log
from bs4 import BeautifulSoup as bs
from selenium.common import exceptions as Except
from selenium import webdriver

log.basicConfig(filename="selenium.log", level=log.DEBUG)


def authenticate(driver, credentials):
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
    auth_url = "https://www.saltybet.com/authenticate?signin=1"
    redirect = "http://www.saltybet.com/"
    driver.get(auth_url)
    elem = driver.find_element_by_id("email")  # In case nothing is found later
    for item in credentials.keys():
        elem = driver.find_element_by_id(item)
        elem.send_keys(credentials[item])
    log.info("Authorization submitted for {}")
    elem.submit()
    if driver.current_url != redirect and \
            driver.current_url == auth_url:
        log.info("Authorization failed properly")
        return False
    elif driver.current_url != redirect:
        log.info("Authorization failed disastrously")
        raise Exception("AuthenticationError: incorrect redirect")
    return True


def get_bettors(source):
    player_bets = {}
    table = source.find("div", id="sbettorswrapper")
    for i, txt in [("1", "redtext"), ("2", "bluetext")]:
        player = table.find('div', id="sbettors" + i).find('span', class_=txt).text
        player_bets[player] = []
        for tag in table.find_all('p', class_='bettor-line'):
            bet = tag.find('span', class_='greentext wager-display')
            bettor = tag.find('strong')
            if bet is not None and bettor is not None:
                player_bets[player].append({'bet': bet.text, 'bettor': bettor.text})
    return player_bets


def get_players(source):
    players = []
    table = source.find('div', id='bet-table')
    for tag in table.find_all('span', class_='submit'):
        players.append(tag.find('input')['value'])
    return players


def get_your_money(source):
    dollar = source.find("span", class_="dollar", id="balance")
    return int(dollar.text) if dollar is not None else 0


def bet_for(source):
    b_for = []
    bet_tag = source.find("span", id="odds")
    if bet_tag.find("span", class_="redtext") is not None:
        b_for.append(bet_tag.text)
        b_for.append(bet_tag.find("span", class_="redtext").text)
        b_for.append(bet_tag.find("span", class_="bluetext").text)
    else:
        b_for = False
    return b_for


def odds(source):
    bet_odds = []
    bet_tag = source.find("span", id="lastbet")
    if bet_tag.find("span", class_="redtext") is not None:
        bet_odds.append(bet_tag.text)
        bet_odds.append(bet_tag.find("span", class_="redtext").text)
        bet_odds.append(bet_tag.find("span", class_="bluetext").text)
    else:
        bet_odds = False
    return bet_odds


def bet(driver, amount, player):
    assert(player == "player1" or player == "player2")
    sent = False
    source = bs(driver.page_source, 'html.parser')
    if "none" in source.find("input", placeholder="Wager")['style'] and False:  # Betting disabled while testing
        elem = driver.find_element_by_id("wager")
        choice = driver.find_element_by_id(player)
        elem.send_keys(str(amount))
        choice.submit()
        sent = True
    return sent


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
    driver = None
    driver_name = ""
    print("Initializing webdriver...")
    for layer, name in [(webdriver.Chrome, "Chrome"),
                        (webdriver.PhantomJS, "PhantomJS")]:
        try:
            driver = layer()
            driver_name = name
            break
        except Except.WebDriverException:
            pass

    if driver is None:
        raise Exception("No webdriver found")

    print("Webdriver %s was initialized" % driver_name)
    print("Querying site...")
    driver.get("https://www.saltybet.com")
    print("Site reached, authenticating...")

    if email is not None and pwrd is not None:
        creds = {"email": email, "pword": pwrd}
    else:
        creds = get_credentials()
    if not authenticate(driver, creds):
        raise Exception("Incorrect credentials, full restart")  # FIXME: should this be handled differently?
    while True:
        source = bs(driver.page_source, 'html.parser')
        print("Placing a bet for player1: {}".format(bet(driver, 1, "player1")))
        print("Odds for players: {}".format(odds(source)))
        print("Total bets for players: {}".format(bet_for(source)))
        print("list of bettors: {} ".format(get_bettors(source).keys()))
        print("Players involved: {}".format(get_players(source)))
        print("Your money: {}".format(get_your_money(source)))
        time.sleep(5)


if __name__ == "__main__":
    try:
        main(email=sys.argv[1], pwrd=sys.argv[2])
    except IndexError:
        main()
