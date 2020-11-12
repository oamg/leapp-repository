import pytest

from leapp.models import (
    CustomTargetRepository,
    CustomTargetRepositoryFile,
    EnvVar,
    Report,
    RepositoryData,
    RHELTargetRepository,
    TargetRepositories,
)
from leapp.libraries.actor import checktargetrepos
from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked


class MockedConsume(object):
    def __init__(self, *args):
        self._msgs = []
        for arg in args:
            if not arg:
                continue
            if isinstance(arg, list):
                self._msgs.extend(arg)
            else:
                self._msgs.append(arg)

    def __call__(self, model):
        return iter([msg for msg in self._msgs if isinstance(msg, model)])


_RHEL_REPOS = [
    RHELTargetRepository(repoid='repo1'),
    RHELTargetRepository(repoid='repo2'),
    RHELTargetRepository(repoid='repo3'),
    RHELTargetRepository(repoid='repo4'),
]

_CUSTOM_REPOS = [
    CustomTargetRepository(repoid='repo1', name='repo1name', baseurl='repo1url', enabled=True),
    CustomTargetRepository(repoid='repo2', name='repo2name', baseurl='repo2url', enabled=False),
    CustomTargetRepository(repoid='repo3', name='repo3name', baseurl=None, enabled=True),
    CustomTargetRepository(repoid='repo4', name='repo4name', baseurl=None, enabled=True),
]

_TARGET_REPOS_CUSTOM = TargetRepositories(rhel_repos=_RHEL_REPOS, custom_repos=_CUSTOM_REPOS)
_TARGET_REPOS_NO_CUSTOM = TargetRepositories(rhel_repos=_RHEL_REPOS)
_CUSTOM_TARGET_REPOFILE = CustomTargetRepositoryFile(file='/etc/leapp/files/leapp_upgrade_repositories.repo')


def test_checktargetrepos_rhsm(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: False)
    monkeypatch.setattr(api, 'consume', MockedConsume())
    checktargetrepos.process()
    assert reporting.create_report.called == 0


@pytest.mark.parametrize('enable_repos', [True, False])
@pytest.mark.parametrize('custom_target_repos', [True, False])
@pytest.mark.parametrize('custom_target_repofile', [True, False])
def test_checktargetrepos_no_rhsm(monkeypatch, enable_repos, custom_target_repos, custom_target_repofile):
    mocked_consume = MockedConsume(_TARGET_REPOS_CUSTOM if custom_target_repos else _TARGET_REPOS_NO_CUSTOM)
    if custom_target_repofile:
        mocked_consume._msgs.append(_CUSTOM_TARGET_REPOFILE)
    envars = {'LEAPP_ENABLE_REPOS': 'hill,spencer'} if enable_repos else {}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars))

    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(rhsm, 'skip_rhsm', lambda: True)
    monkeypatch.setattr(api, 'consume', mocked_consume)

    checktargetrepos.process()

    if not custom_target_repos:
        assert reporting.create_report.called == 1
        assert 'inhibitor' in reporting.create_report.report_fields.get('groups', [])
    elif not enable_repos and custom_target_repos and not custom_target_repofile:
        assert reporting.create_report.called == 1
        assert 'inhibitor' not in reporting.create_report.report_fields.get('groups', [])
    else:
        assert reporting.create_report.called == 0
