#! /usr/bin/env python3


class DatabaseException(Exception):
    """ Base class for database exceptions for future reasons"""


class TableCreationError(DatabaseException):
    """ A table was not created """


class InsertionError(DatabaseException):
    """ The insertion did not occur """
