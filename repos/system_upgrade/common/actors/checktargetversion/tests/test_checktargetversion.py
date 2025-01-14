import os

import pytest

from leapp import reporting
from leapp.libraries.actor import checktargetversion
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import IPUPath, IPUPaths
from leapp.utils.deprecation import suppress_deprecation
from leapp.utils.report import is_inhibitor


# It must be in a function so we can suppress the deprecation warning in tests.
@suppress_deprecation(IPUPaths)
def _get_upgrade_paths_data():
    return IPUPaths(data=[
        IPUPath(source_version='7.9', target_versions=['8.10']),
        IPUPath(source_version='8.10', target_versions=['9.4', '9.5', '9.6']),
        IPUPath(source_version='9.6', target_versions=['10.0']),
        IPUPath(source_version='7', target_versions=['8.10']),
        IPUPath(source_version='8', target_versions=['9.4', '9.5', '9.6']),
        IPUPath(source_version='9', target_versions=['10.0'])
    ])


@pytest.fixture
def setup_monkeypatch(monkeypatch):
    """Fixture to set up common monkeypatches."""

    def _setup(source_version, target_version, leapp_unsupported='0'):
        curr_actor_mocked = CurrentActorMocked(
            src_ver=source_version,
            dst_ver=target_version,
            envars={'LEAPP_UNSUPPORTED': leapp_unsupported},
            msgs=[_get_upgrade_paths_data()]
        )
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(api, 'current_logger', logger_mocked())
        monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    return _setup


@pytest.mark.parametrize(('source_version', 'target_version', 'leapp_unsupported'), [
    # LEAPP_UNSUPPORTED=0
    ('7.9', '9.0', '0'),
    ('8.10', '9.0', '0'),
    ('9.6', '10.1', '0'),
    ('7', '9.0', '0'),
    ('8', '9.0', '0'),
    ('9', '10.1', '0'),
    # LEAPP_UNSUPPORTED=1
    ('7.9', '9.0', '1'),
    ('8.10', '9.0', '1'),
    ('9.6', '10.1', '1'),
    ('7', '9.0', '1'),
    ('8', '9.0', '1'),
    ('9', '10.1', '1'),
])
def test_unsuppoted_paths(setup_monkeypatch, source_version, target_version, leapp_unsupported):
    setup_monkeypatch(source_version, target_version, leapp_unsupported)

    if leapp_unsupported == '1':
        checktargetversion.process()
        assert reporting.create_report.called == 0
        assert api.current_logger.warnmsg
    else:
        checktargetversion.process()
        assert reporting.create_report.called == 1
        assert is_inhibitor(reporting.create_report.report_fields)


@pytest.mark.parametrize(('source_version', 'target_version'), [
    ('7.9', '8.10'),
    ('8.10', '9.4'),
    ('8.10', '9.5'),
    ('8.10', '9.6'),
    ('9.6', '10.0'),
    ('7', '8.10'),
    ('8', '9.4'),
    ('8', '9.5'),
    ('8', '9.6'),
    ('9', '10.0'),
])
def test_supported_paths(setup_monkeypatch, source_version, target_version):
    setup_monkeypatch(source_version, target_version, leapp_unsupported='0')

    checktargetversion.process()
    assert reporting.create_report.called == 0
    assert api.current_logger.infomsg
