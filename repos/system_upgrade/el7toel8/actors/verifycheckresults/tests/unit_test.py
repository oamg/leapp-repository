from collections import namedtuple
import json

from leapp.libraries.actor import library
from leapp.libraries.stdlib import api
from leapp import reporting


class Report(object):
    def __init__(self, message):
        self.message = message

    def get(self, _, __):
        if self.message == 'title_with_inhibitor':
            return ['inhibitor']
        return []

    def __getitem__(self, _):
        return self.message


class ReportError(object):
    def __init__(self):
        self.message = None
        self.called = 0

    def set(self, message):
        self.called += 1
        self.message = message


def test_actor(monkeypatch):
    def report_mocked(*models):
        yield namedtuple('msg', ['report'])(Report('title_with_inhibitor'))

    report_error = ReportError()
    monkeypatch.setattr(api, "consume", report_mocked)
    monkeypatch.setattr(api, "report_error", report_error.set)
    library.check()
    assert report_error.message == 'title_with_inhibitor'
    assert report_error.called == 1


def test_actor_no_inhibitor(monkeypatch):
    def report_mocked(*models):
        yield namedtuple('msg', ['report'])(Report('title_without_inhibitor'))

    report_error = ReportError()
    monkeypatch.setattr(api, "consume", report_mocked)
    monkeypatch.setattr(api, "report_error", report_error.set)
    library.check()
    assert not report_error.message
    assert report_error.called == 0
