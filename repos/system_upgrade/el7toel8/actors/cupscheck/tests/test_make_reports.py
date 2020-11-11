import pytest

from leapp.libraries.actor.cupscheck import make_reports


class MockLogger(object):
    def __init__(self):
        self.debug_msg = ''

    def debug_log(self, msg):
        self.debug_msg += msg


class MockInputFacts(object):
    def __init__(self, facts):
        self.facts = facts

    def get_facts(self, model):
        ret = None
        if model == 'CupsChangedFeatures':
            ret = self.facts

        return ret


class MockReport(object):
    def __init__(self):
        self.report = []

    # unused, report testing will be done separately
    def create_report(self, data_list):
        if data_list:
            self.report.append(data_list)


def test_make_reports():

    logger = MockLogger()
    facts = MockInputFacts(None)
    reporting = MockReport()

    make_reports(facts.get_facts, reporting.create_report, logger.debug_log)

    assert logger.debug_msg == 'No facts gathered about CUPS - skipping reports.'
