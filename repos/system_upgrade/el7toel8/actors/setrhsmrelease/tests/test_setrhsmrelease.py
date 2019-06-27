from leapp.libraries.actor import setrelease
from leapp.libraries.common import mounting, rhsm
from leapp.libraries.stdlib import api
from leapp.models import TargetRHSMInfo


def not_isolated_actions():
    commands_called = []

    class MockNotIsolatedActions(object):
        def __init__(self, base_dir=None):
            pass

        def call(self, cmd, **kwargs):
            commands_called.append((cmd, kwargs))
    return (commands_called, MockNotIsolatedActions)


def test_setrelease(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in (TargetRHSMInfo(release='6.6.6'),)))
    setrelease.process()
    assert commands_called and len(commands_called) == 1
    assert commands_called[0][0][-1] == '6.6.6'


def test_setrelease_no_message(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in ()))
    setrelease.process()
    assert not commands_called


def test_setrelease_skip_rhsm(monkeypatch):
    commands_called, klass = not_isolated_actions()
    monkeypatch.setenv('LEAPP_DEVEL_SKIP_RHSM', '1')
    # To make this work we need to re-apply the decorator, so it respects the environment variable
    monkeypatch.setattr(rhsm, 'set_release', rhsm.with_rhsm(rhsm.set_release))
    monkeypatch.setattr(mounting, 'NotIsolatedActions', klass)
    monkeypatch.setattr(api, 'consume', lambda *x: (x for x in (TargetRHSMInfo(release='6.6.6'),)))
    setrelease.process()
    assert not commands_called
