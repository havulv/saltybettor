'''
Custom Exceptions will go here

'''


class AuthenticationError(Exception):

    def __init__(self):
        self.message = ("There was an error Authenticating the email and "
                        "password with the service.")
