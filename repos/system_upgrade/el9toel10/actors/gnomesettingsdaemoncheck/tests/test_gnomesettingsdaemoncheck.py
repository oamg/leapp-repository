import pytest

from leapp.libraries.actor import gnomesettingsdaemoncheck
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import RpmTransactionTasks


@pytest.mark.parametrize('env_installed', [True, False])
def test_install_task_produced(monkeypatch, env_installed):
    monkeypatch.setattr(
        gnomesettingsdaemoncheck,
        '_is_graphical_server_environment_installed',
        lambda: env_installed,
    )
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())
    monkeypatch.setattr(api, 'produce', produce_mocked())

    gnomesettingsdaemoncheck.process()

    if env_installed:
        assert api.produce.called == 1
        task = api.produce.model_instances[0]
        assert isinstance(task, RpmTransactionTasks)
        assert gnomesettingsdaemoncheck.GSD_SERVER_DEFAULTS_PKG in task.to_install
    else:
        assert api.produce.called == 0


def test_dnf_unavailable(monkeypatch):
    monkeypatch.setattr(gnomesettingsdaemoncheck, 'no_dnf', True)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    result = gnomesettingsdaemoncheck._is_graphical_server_environment_installed()

    assert result is False


def test_dnf_exception_handled(monkeypatch):
    class FakeSwdb:
        def getCompsEnvironmentItemsByPattern(self, pattern):
            raise RuntimeError('db error')

    class FakeHistory:
        swdb = FakeSwdb()

    class FakeBase:
        history = FakeHistory()

    monkeypatch.setattr(gnomesettingsdaemoncheck, 'no_dnf', False)
    monkeypatch.setattr(gnomesettingsdaemoncheck, 'dnf', type('dnf', (), {'Base': FakeBase}))
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    result = gnomesettingsdaemoncheck._is_graphical_server_environment_installed()

    assert result is False
