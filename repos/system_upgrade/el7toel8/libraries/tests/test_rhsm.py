from collections import namedtuple

import pytest

from leapp import reporting
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import repofileutils, rhsm
from leapp.libraries.common.testutils import create_report_mocked, logger_mocked
from leapp.libraries.stdlib import CalledProcessError, api
from leapp.models import RepositoryFile, RepositoryData

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


def _gen_repo(repoid):
    return RepositoryData(repoid=repoid, name='name {}'.format(repoid))


def _gen_repofile(rfile, data=None):
    if data is None:
        data = [_gen_repo("{}-{}".format(rfile.split("/")[-1], i)) for i in range(3)]
    return RepositoryFile(file=rfile, data=data)


@pytest.mark.parametrize('other_repofiles', [
    [],
    [_gen_repofile("foo")],
    [_gen_repofile("foo"), _gen_repofile("bar")],
])
@pytest.mark.parametrize('rhsm_repofile', [
    None,
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE, []),
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE, [_gen_repo("rh-0")]),
    _gen_repofile(rhsm._DEFAULT_RHSM_REPOFILE),
])
def test_get_available_repo_ids(monkeypatch, other_repofiles, rhsm_repofile):
    context_mocked = IsolatedActionsMocked()
    repos = other_repofiles[:]
    if rhsm_repofile:
        repos.append(rhsm_repofile)
    rhsm_repos = [repo.repoid for repo in rhsm_repofile.data] if rhsm_repofile else []

    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(rhsm, '_inhibit_on_duplicate_repos', lambda x: None)
    monkeypatch.setattr(repofileutils, 'get_parsed_repofiles', lambda x: repos)

    result = rhsm.get_available_repo_ids(context_mocked)

    rhsm_repos.sort()
    assert context_mocked.commands_called == [['yum', 'clean', 'all']]
    assert result == rhsm_repos
    if result:
        msg = (
            'The following repoids are available through RHSM:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(rhsm_repos))
        )
        assert msg in api.current_logger.infomsg
    else:
        assert 'There are no repos available through RHSM.' in api.current_logger.infomsg


def test_get_available_repo_ids_error():
    context_mocked = IsolatedActionsMocked(raise_err=True)

    with pytest.raises(StopActorExecutionError) as err:
        rhsm.get_available_repo_ids(context_mocked)

    assert 'Unable to use yum' in str(err)


def test_inhibit_on_duplicate_repos(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    repofiles = [
        _gen_repofile("foo", [_gen_repo('repoX'), _gen_repo('repoY')]),
        _gen_repofile("bar", [_gen_repo('repoX')]),
    ]

    rhsm._inhibit_on_duplicate_repos(repofiles)

    dups = ['repoX']
    assert ('The following repoids are defined multiple times:{0}{1}'
            .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups))) in api.current_logger.warnmsg
    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['groups']
    assert reporting.create_report.report_fields['title'] == 'A YUM/DNF repository defined multiple times'
    summary = ('The following repositories are defined multiple times:{0}{1}'
               .format(LIST_SEPARATOR, LIST_SEPARATOR.join(dups)))
    assert summary in reporting.create_report.report_fields['summary']


def test_inhibit_on_duplicate_repos_no_dups(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    rhsm._inhibit_on_duplicate_repos([_gen_repofile("foo")])

    assert not api.current_logger.warnmsg
    assert reporting.create_report.called == 0
