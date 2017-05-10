'''
Saltbot
---

Main file for controling the bot
    while it gathers information

'''

from .saltbot import SaltBot
from .helpers import get_credentials
import threading
import sys


def main_thread(bot):
    if bot.load():
        print("Database loaded into memory")
    bot.record()


def main(email=None, pwrd=None):
    drive = input("Specific driver? ")
    if drive == "no":
        drive = None

    if len(sys.argv) == 3:
        creds = {'email': sys.argv[2],
                 'pword': sys.argv[3]}
    else:
        creds = get_credentials()

    salt_bot = SaltBot(creds, driver=drive)

    main_loop = threading.Thread(target=main_thread, args=(salt_bot,))
    main_loop.start()
    main_loop.join()
