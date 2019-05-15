import os


def make_IOError(error):
    '''
    Create an IOError instance

    Create an IOError instance with the given error number.

    :param error: the error number, e.g. errno.ENOENT
    '''
    return IOError(error, os.strerror(error))


def make_OSError(error):
    '''
    Create an OSError instance

    Create an OSError instance with the given error number.

    :param error: the error number, e.g. errno.ENOENT
    '''
    return OSError(error, os.strerror(error))
