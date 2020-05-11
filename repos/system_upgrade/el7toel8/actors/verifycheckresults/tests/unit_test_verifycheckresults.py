from collections import namedtuple

import pytest

from leapp.exceptions import RequestStopAfterPhase
from leapp.libraries.actor import verifycheckresults
from leapp.libraries.stdlib import api


class Report(object):
    def __init__(self, message):
        self.message = message

    def get(self, _, __):
        if self.message == 'title_with_inhibitor':
            return ['inhibitor']
        return []

    def __getitem__(self, _):
        return self.message


def test_actor(monkeypatch):
    def report_mocked(*models):
        yield namedtuple('msg', ['report'])(Report('title_with_inhibitor'))

    monkeypatch.setattr(api, "consume", report_mocked)

    with pytest.raises(RequestStopAfterPhase):
        verifycheckresults.check()


def test_actor_no_inhibitor(monkeypatch):
    def report_mocked(*models):
        yield namedtuple('msg', ['report'])(Report('title_without_inhibitor'))

    monkeypatch.setattr(api, "consume", report_mocked)
    verifycheckresults.check()
