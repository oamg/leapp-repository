from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import rhsm
from leapp.libraries.common.testutils import create_report_mocked
from leapp.libraries.stdlib import CalledProcessError, api

Repository = namedtuple('Repository', ['repoid', 'file'])
LIST_SEPARATOR = '\n    - '


class IsolatedActionsMocked(object):
    def __init__(self, call_stdout=None, raise_err=False):
        self.commands_called = []
        self.call_return = {'stdout': call_stdout, 'stderr': None}
        self.raise_err = raise_err

    def call(self, cmd, *args):
        self.commands_called.append(cmd)
        if self.raise_err:
            raise_call_error(cmd)
        return self.call_return


def raise_call_error(args=None, exit_code=1):
    raise CalledProcessError(
        message='Command {0} failed with exit code {1}.'.format(str(args), exit_code),
        command=args,
        result={'signal': None, 'exit_code': exit_code, 'pid': 0, 'stdout': 'fake out', 'stderr': 'fake err'}
    )


class LoggerMocked(object):
    def __init__(self):
        self.infomsg = None
        self.warnmsg = None

    def info(self, msg):
        self.infomsg = msg

    def warn(self, msg):
        self.warnmsg = msg

    def __call__(self):
        return self


@pytest.mark.parametrize('releasever', ['8.2', None])
@pytest.mark.parametrize('available_repos', [
    [],
    [Repository(repoid='repoidX', file=rhsm._DEFAULT_RHSM_REPOFILE),
     Repository(repoid='repoidY', file='random_test_file')]
])
def test_get_available_repo_ids(monkeypatch, releasever, available_repos):
    context_mocked = IsolatedActionsMocked()
    monkeypatch.setattr(rhsm, '_inhibit_on_duplicate_repos', lambda x: None)
    monkeypatch.setattr(rhsm, '_get_repos', lambda x: iter(available_repos))
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())

    available_repos = rhsm.get_available_repo_ids(context_mocked, releasever)

    if releasever:
        assert context_mocked.commands_called == [['yum', 'repoinfo', '--releasever', '8.2']]
    else:
        assert context_mocked.commands_called == [['yum', 'repoinfo']]
    if available_repos:
        available_repoid = 'repoidX'
        assert available_repos == [available_repoid]
        assert api.current_logger.infomsg == (
            'The following repoids are available through RHSM:{0}{1}'
            .format(LIST_SEPARATOR, available_repoid))
    else:
        assert available_repos == []
        assert api.current_logger.infomsg == 'There are no repos available through RHSM.'


def test_get_available_repo_ids_error():
    context_mocked = IsolatedActionsMocked(raise_err=True)

    with pytest.raises(StopActorExecutionError) as err:
        rhsm.get_available_repo_ids(context_mocked)

    assert 'Unable to get list of available yum repositories.' in str(err)
    assert "Command ['yum', 'repoinfo'] failed" in err.value.details['details']


YUM_REPOINFO_TYPICAL = ("""
Repo-id      : custom-repo-id
Repo-name    : Custom repository
Repo-revision: 1583940534
Repo-updated : Wed Mar 11 15:28:55 2020
Repo-pkgs    : 548
Repo-size    : 1.2 G
Repo-baseurl : http://custom-repo-url/
Repo-expire  : 21,600 second(s) (last: Wed Mar 11 16:05:04 2020)
  Filter     : read-only:present
Repo-excluded: 205
Repo-filename: /etc/yum.repos.d/custom-repo.repo

Repo-id      : rhel-7-server-rpms/7Server/x86_64
Repo-name    : Red Hat Enterprise Linux 7 Server (RPMs)
Repo-revision: 1583726307
Repo-updated : Mon Mar  9 03:58:27 2020
Repo-pkgs    : 5,231
Repo-size    : 3.6 G
Repo-baseurl : https://cdn.redhat.com/content/dist/rhel/server/7/7Server/x86_64/os
Repo-expire  : 86,400 second(s) (last: Mon Mar  9 21:06:18 2020)
  Filter     : read-only:present
Repo-filename: /etc/yum.repos.d/redhat.repo

repolist: 5,779
""")


YUM_REPOINFO_DUPS = ("""
Repository rhel-7-server-eus-rpms is listed more than once in the configuration
Repository rhel-7-server-extras-rpms is listed more than once in the configuration
Repository rhel-7-server-eus-optional-rpms is listed more than once in the configuration
""")


def test_inhibit_on_duplicate_repos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())

    rhsm._inhibit_on_duplicate_repos(YUM_REPOINFO_DUPS + YUM_REPOINFO_TYPICAL)

    dups = ['rhel-7-server-eus-rpms', 'rhel-7-server-extras-rpms', 'rhel-7-server-eus-optional-rpms']
    assert ('The following repoids are defined multiple times:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups))) in api.current_logger.warnmsg
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['flags']
    assert reporting.create_report.report_fields['title'] == 'A YUM/DNF repository defined multiple times'
    assert ('the following repositories are defined multiple times:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups))) in reporting.create_report.report_fields['summary']


def test_inhibit_on_duplicate_repos_no_dups(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', LoggerMocked())

    rhsm._inhibit_on_duplicate_repos(YUM_REPOINFO_TYPICAL)

    assert api.current_logger.warnmsg is None
    assert reporting.create_report.called == 0


def test_get_repos():
    repos = list(rhsm._get_repos(YUM_REPOINFO_TYPICAL))

    assert repos == [Repository(repoid='custom-repo-id', file='/etc/yum.repos.d/custom-repo.repo'),
                     Repository(repoid='rhel-7-server-rpms', file='/etc/yum.repos.d/redhat.repo')]


# There's an additional space between 'Repo-filename' and ':'
YUM_REPOINFO_ADDITIONAL_SPACE = ("""Repo-id      : rhel-7-server-rpms/7Server/x86_64
Repo-name    : Red Hat Enterprise Linux 7 Server (RPMs)
Repo-revision: 1583726307
Repo-updated : Mon Mar  9 03:58:27 2020
Repo-pkgs    : 5,231
Repo-size    : 3.6 G
Repo-baseurl : https://cdn.redhat.com/content/dist/rhel/server/7/7Server/x86_64/os
Repo-expire  : 86,400 second(s) (last: Mon Mar  9 21:06:18 2020)
  Filter     : read-only:present
Repo-filename : /etc/yum.repos.d/redhat.repo""")


def test_parse_repo_params():
    with pytest.raises(StopActorExecutionError) as err:
        rhsm._parse_repo_params(YUM_REPOINFO_ADDITIONAL_SPACE)

    assert 'Failed to parse the `yum repoinfo` output' in str(err)
    assert ("Failed to parse the 'Repo-filename' repo parameter within the following part of the `yum repoinfo`"
            " output:\n{0}".format(YUM_REPOINFO_ADDITIONAL_SPACE)) in err.value.details['details']
