import pytest

from leapp.libraries.actor import checkremovedenvvars
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.utils.report import is_inhibitor


def test_removed_vars(monkeypatch):
    envars = {'LEAPP_GRUB_DEVICE': '/dev/sda'}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars))
    monkeypatch.setattr(api.current_actor, "produce", produce_mocked())
    checkremovedenvvars.process()
    assert api.current_actor.produce.called == 1
    assert 'LEAPP_GRUB_DEVICE' in api.current_actor.produce.model_instances[0].report['summary']
    assert is_inhibitor(api.current_actor.produce.model_instances[0].report)


def test_no_removed_vars(monkeypatch):
    envars = {'LEAPP_SKIP_RHSM': '1'}
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(envars=envars))
    monkeypatch.setattr(api.current_actor, "produce", produce_mocked())
    checkremovedenvvars.process()
    assert not api.current_actor.produce.called
    assert not api.current_actor.produce.model_instances
