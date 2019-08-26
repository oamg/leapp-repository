import sys

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import library
from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import CalledProcessError, api
from leapp.models import (TargetRHSMInfo, UsedTargetRepositories,
                          UsedTargetRepository)


def not_isolated_actions(raise_err=False):
    commands_called = []

    class MockNotIsolatedActions(object):
        def __init__(self, base_dir=None):
            pass

        def call(self, cmd, **kwargs):
            commands_called.append((cmd, kwargs))
            if raise_err:
                raise_call_error()

    return (commands_called, MockNotIsolatedActions)


def raise_call_error(args=None):
    raise CalledProcessError(
        message='A Leapp Command Error occured.',
        command=args,
        result={'signal': None, 'exit_code': 1, 'pid': 0, 'stdout': 'fake', 'stderr': 'fake'}
    )


class run_mocked(object):
    def __init__(self, raise_err=False):
        self.called = 0
        self.args = []
        self.raise_err = raise_err

    def __call__(self, *args):
        self.called += 1
        self.args.append(args)
        if self.raise_err:
            raise_call_error(args)


class logger_mocked(object):
    def __init__(self):
        self.warnmsg = None
        self.dbgmsg = None

    def warning(self, *args):
        self.warnmsg = args

    def debug(self, *args):
        self.dbgmsg = args

    def __call__(self):
        return self


def test_setrelease(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in (TargetRHSMInfo(release='6.6'),)))
    library.set_rhsm_release()
    assert commands_called and len(commands_called) == 1
    assert commands_called[0][0][-1] == '6.6'


def test_setrelease_no_message(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in ()))
    library.set_rhsm_release()
    assert not commands_called


def test_setrelease_submgr_throwing_error(monkeypatch):
    _, klass = not_isolated_actions(raise_err=True)
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in (TargetRHSMInfo(release='6.6'),)))
    # free the set_release funtion from the @_rhsm_retry decorator which would otherwise cause 25 sec delay of the test
    if sys.version_info.major < 3:
        monkeypatch.setattr(rhsm, 'set_release', rhsm.set_release.func_closure[0].cell_contents)
    else:
        monkeypatch.setattr(rhsm, 'set_release', rhsm.set_release.__wrapped__)
    with pytest.raises(StopActorExecutionError):
        library.set_rhsm_release()


def test_setrelease_skip_rhsm(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_RHSM', '1')
    # To make this work we need to re-apply the decorator, so it respects the environment variable
    monkeypatch.setattr(rhsm, 'set_release', rhsm.with_rhsm(rhsm.set_release))
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in (TargetRHSMInfo(release='6.6'),)))
    library.set_rhsm_release()
    assert not commands_called


def construct_UTRepo_consume(repoids):
    repos = [UsedTargetRepository(repoid=repoid) for repoid in repoids]
    return lambda *x: (x for x in (UsedTargetRepositories(repos=repos),))


def test_get_unique_repoids(monkeypatch):
    repoids = (['some-repo', 'some-repo', 'another-repo'])
    monkeypatch.setattr(api, 'consume', construct_UTRepo_consume(repoids))
    assert library.get_repos_to_enable() == {'some-repo', 'another-repo'}


def test_get_submgr_cmd():
    assert library.get_submgr_cmd({'some-repo'}) == ['subscription-manager', 'repos', '--enable', 'some-repo']


def test_running_submgr_ok(monkeypatch):
    monkeypatch.setattr(library, 'get_repos_to_enable', lambda: {'some-repo'})
    monkeypatch.setattr(library, 'run', run_mocked())
    library.enable_rhsm_repos()
    assert library.run.called
    assert 'subscription-manager' in library.run.args[0][0]


def test_running_submgr_fail(monkeypatch):
    monkeypatch.setattr(library, 'get_repos_to_enable', lambda: {'some-repo'})
    monkeypatch.setattr(library, 'run', run_mocked(raise_err=True))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    library.enable_rhsm_repos()
    assert library.run.called
    assert api.current_logger.warnmsg


def test_enable_repos_skip_rhsm(monkeypatch):
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_RHSM', '1')
    monkeypatch.setattr(library, 'run', run_mocked())
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    library.enable_rhsm_repos()
    assert not library.run.called
    assert api.current_logger.dbgmsg
