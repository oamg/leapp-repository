import os


class produce_mocked(object):
    def __init__(self):
        self.called = 0
        self.model_instances = []

    def __call__(self, *model_instances):
        self.called += 1
        self.model_instances.append(model_instances[0])


class report_generic_mocked(object):
    def __init__(self):
        self.called = 0
        self.report_fields = None

    def __call__(self, **report_fields):
        self.called += 1
        self.report_fields = report_fields


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
