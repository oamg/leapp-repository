import pytest

from leapp.libraries.actor import gnomesettingsdaemoncheck
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import DNFEnvironment, InstalledDNFComps, RpmTransactionTasks


def _installed_comps(env_ids=None):
    envs = [DNFEnvironment(id=eid, name=eid) for eid in (env_ids or [])]
    return InstalledDNFComps(environments=envs)


@pytest.mark.parametrize('env_ids,expected', [
    ([gnomesettingsdaemoncheck.GRAPHICAL_SERVER_ENV], True),
    ([gnomesettingsdaemoncheck.GRAPHICAL_SERVER_ENV, 'minimal-environment'], True),
    (['minimal-environment'], False),
    ([], False),
])
def test_is_graphical_server_environment_installed(env_ids, expected):
    comps = _installed_comps(env_ids)
    assert gnomesettingsdaemoncheck._is_graphical_server_environment_installed(comps) is expected


def test_process_produces_install_task(monkeypatch):
    comps = _installed_comps([gnomesettingsdaemoncheck.GRAPHICAL_SERVER_ENV])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[comps]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    gnomesettingsdaemoncheck.process()

    assert api.produce.called == 1
    task = api.produce.model_instances[0]
    assert isinstance(task, RpmTransactionTasks)
    assert gnomesettingsdaemoncheck.GSD_SERVER_DEFAULTS_PKG in task.to_install


def test_process_no_install_when_env_not_present(monkeypatch):
    comps = _installed_comps(['minimal-environment'])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[comps]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    gnomesettingsdaemoncheck.process()

    assert api.produce.called == 0


def test_process_no_install_when_no_comps_message(monkeypatch):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    gnomesettingsdaemoncheck.process()

    assert api.produce.called == 0
