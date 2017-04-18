
# Saltybetter

A bot for placing bets on [SaltyBet](https://www.saltybet.com), running off of selenium and the Gmail API (email alerts).

## Installation

Currently requires setup of the [Gmail API](https://developers.google.com/gmail/api/quickstart/python) and works off of the [Chrome Webdriver](https://sites.google.com/a/chromium.org/chromedriver/downloads). Eventually this will be done from PhantomJS, so users be warned.

First, clone the repo and download the driver mentioned above and add it to your `PATH`.

Then, after you have downloaded the Chrome Webdriver and added the containing directory to your `PATH` environment variable:

    `pip install selenium`
    `pip install google-api-client`
    `pip install httplib2`
    `pip install oauth2client`

Then follow the [Gmail API](https://developers.google.com/gmail/api/quickstart/python) setup to get the credentials all setup. Then you should be good to go!

Eventually I will get this running and then make the gmail dependency disappear because that is about 3/4 of the current dependencies.

