from multiprocessing import Manager

from leapp.models import SatelliteFacts, SatellitePostgresqlFacts
from leapp.snactor.fixture import current_actor_context


class MockedRun(object):
    def __init__(self):
        self._manager = Manager()
        self.commands = self._manager.list()

    def __call__(self, cmd, *args, **kwargs):
        self.commands.append(cmd)
        return {}


def test_run_installer(monkeypatch, current_actor_context):
    mocked_run = MockedRun()
    monkeypatch.setattr('leapp.libraries.stdlib.run', mocked_run)
    current_actor_context.feed(SatelliteFacts(has_foreman=True, postgresql=SatellitePostgresqlFacts()))
    current_actor_context.run()
    assert mocked_run.commands
    assert len(mocked_run.commands) == 1
    assert mocked_run.commands[0] == ['foreman-installer', '--disable-system-checks']


def test_run_installer_without_katello(monkeypatch, current_actor_context):
    mocked_run = MockedRun()
    monkeypatch.setattr('leapp.libraries.stdlib.run', mocked_run)
    current_actor_context.feed(SatelliteFacts(has_foreman=True, has_katello_installer=False,
                                              postgresql=SatellitePostgresqlFacts()))
    current_actor_context.run()
    assert mocked_run.commands
    assert len(mocked_run.commands) == 1
    assert mocked_run.commands[0] == ['foreman-installer']
