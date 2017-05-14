#!/usr/bin/python3

'''
    Google API classes

'''

import logging
import httplib2
import os
from apiclient import errors
from apiclient.discovery import build
from oauth2client import client, file, tools
from email.mime.text import MIMEText
import base64

logging.basicConfig(filename="gAPI.log", level=logging.DEBUG)


class gAPI(object):

    def __init__(self):
        self._APPLICATION_NAME = None
        self._SCOPES = None
        self._CLIENT_SECRET_DIR = self._form_client_secret_path()
        self._CLIENT_SECRET_FILE = 'client_secret.json'
        self._refresh = False

    def _form_client_secret_path(self):
        ''' Form the path to the client secret file'''
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            logging.info("{} doesn't exist"
                         " -- Creating directory".format(
                             credential_dir))
            os.makedirs(credential_dir)
        credential_dir = os.path.join(credential_dir,
                                      self.__class__.__name__)
        if not os.path.exists(credential_dir):
            logging.info("{} doesn't exist"
                         " -- Creating directory".format(
                             credential_dir))
            os.makedirs(credential_dir)
        return credential_dir

    def _initialize_api_http(self):
        ''' Initializes an analytics instance for API access '''
        if self._SCOPES is None:
            raise Exception("Scope Error, please read the gAPI docs")
        credential_dir = self._CLIENT_SECRET_DIR
        credential_path = os.path.join(credential_dir,
                                       self.__class__.__name__ + '.dat')

        secret = os.path.join(credential_dir,
                              self._CLIENT_SECRET_FILE)

        # In case of no authentication; set it up
        storage = file.Storage(credential_path)
        credentials = storage.get()
        if not credentials or credentials.invalid or self._refresh:
            logging.info("Invalid credentials in {}".format(
                os.path.dirname(credential_path)))
            flow = client.flow_from_clientsecrets(
                secret, scope=self._SCOPES,
                message=tools.message_if_missing(secret))
            if self.APPLICATION_NAME:
                flow.user_agent = self._APPLICATION_NAME
            credentials = tools.run_flow(flow, storage)

        return credentials.authorize(http=httplib2.Http())


class gmail(gAPI):

    def __init__(self):
        super().__init__()
        self._SCOPES = ['https://mail.google.com']
        self.APPLICATION_NAME = 'Gmail Notifications'
        self._api_gmail = self._build_http_access()
        self._message = False
        self._refresh = True

    def _build_http_access(self):
        http = super()._initialize_api_http()
        service = build('gmail', 'v1', http=http)
        return service

    def create_message(self, sender, to, subject, message_text):
        logging.info("Creating message from {} to {}".format(sender, to))
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        self._message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}

    def send_mail(self):
        logging.info("Sending message")
        if not self._message:
            # FIXME: put in a more informative error and shit
            raise ValueError
        try:
            message = self._api_gmail.users().messages().send(
                userId="me", body=self._message).execute()
            return message
        except errors.HttpError as error:
            logging.debug('An error occurred: {0}'.format(error))


if __name__ == "__main__":
    mail = gmail()
    print(mail._SCOPES)
