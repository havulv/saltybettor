"""
Saltbot
---

A betting bot for [SaltyBet](http://saltybet.com)

"""

__version__ = '0.1.1'


from .saltbot import SaltBot
from .database import betdb
from .gAPI import gmail
from .exceptions import AuthenticationError
from .helpers import Log, keyboardwrap, get_credentials


__all__ = [
    '__version__',

    'AuthenticationError',

    'Log', 'keyboardwrap', 'get_credentials',

    'gmail', 'betdb', 'SaltBot'
]
