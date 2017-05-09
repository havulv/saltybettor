'''
SaltBot
---

A file for helper functions

'''

import logging as log


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


class Log(object):
    def write(self, msg):
        log.info(msg)


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
