from collections import namedtuple

import pytest

from leapp import reporting
from leapp.libraries.actor import library
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked
from leapp.libraries.stdlib import api


class CurrentActorMocked(object):
    def __init__(self, src_ver='7.6', dst_ver='8.1'):

        version = namedtuple('Version', ['source', 'target'])(src_ver, dst_ver)
        self.configuration = namedtuple('configuration', ['version'])(version)

    def __call__(self):
        return self


@pytest.mark.parametrize('version', ['8.{}'.format(i) for i in range(4)])
def test_report_target_version(monkeypatch, version):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver=version))
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    SUMMARY_FMT = 'will be set to {}.'
    library.process()
    assert reporting.create_report.called == 1
    assert SUMMARY_FMT.format(version) in reporting.create_report.report_fields['summary']
    assert 'is going to be set' in reporting.create_report.report_fields['title']


def test_report_unhandled_release(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(dst_ver='8.1'))
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    library.process()
    assert reporting.create_report.called == 1
    assert 'is going to be kept' in reporting.create_report.report_fields['title']
