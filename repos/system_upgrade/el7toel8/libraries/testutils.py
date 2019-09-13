import os


class produce_mocked(object):
    def __init__(self):
        self.called = 0
        self.model_instances = []

    def __call__(self, *model_instances):
        self.called += len(model_instances)
        self.model_instances.extend(list(model_instances))


class create_report_mocked(object):
    def __init__(self):
        self.called = 0
        self.report_fields = {}

    def __call__(self, report_fields):
        self.called += 1
        # iterate list of report primitives (classes)
        for report in report_fields:
            # last element of path is our field name
            self.report_fields.update(report.to_dict())


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
