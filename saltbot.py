#! /usr/bin/env python3

''' Potentially use PhantomJS instead of Chrome webdriver '''

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


def get_your_money(source):
    dollar = source.find("span", class_="dollar", id="balance")
    return int(dollar.text) if dollar is not None else 0


def odds(source):
    b_odds = []
    for tag in source.find_all("span", id="odds"):
        b_odds(tag.find("li").text)
        b_odds.append(tag.find("span", class_="redtext").text)
        b_odds.append(tag.find("span", class_="bluetext").text)
    return b_odds


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
    source = bs(driver.page_source, 'html.parser')
    print(bet(driver, 1, "player1"), odds(source))


if __name__ == "__main__":
    try:
        main(email=sys.argv[1], pwrd=sys.argv[2])
    except IndexError:
        main()
