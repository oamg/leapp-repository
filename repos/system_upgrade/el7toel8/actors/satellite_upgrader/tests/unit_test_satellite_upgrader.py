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
    current_actor_context.feed(SatelliteFacts(has_foreman=True,
                                              postgresql=SatellitePostgresqlFacts(local_postgresql=False)))
    current_actor_context.run()
    assert mocked_run.commands
    assert len(mocked_run.commands) == 1
    assert mocked_run.commands[0] == ['foreman-installer', '--disable-system-checks']


def test_run_installer_without_katello(monkeypatch, current_actor_context):
    mocked_run = MockedRun()
    monkeypatch.setattr('leapp.libraries.stdlib.run', mocked_run)
    current_actor_context.feed(SatelliteFacts(has_foreman=True, has_katello_installer=False,
                                              postgresql=SatellitePostgresqlFacts(local_postgresql=False)))
    current_actor_context.run()
    assert mocked_run.commands
    assert len(mocked_run.commands) == 1
    assert mocked_run.commands[0] == ['foreman-installer']


def test_run_reindexdb(monkeypatch, current_actor_context):
    mocked_run = MockedRun()
    monkeypatch.setattr('leapp.libraries.stdlib.run', mocked_run)
    current_actor_context.feed(SatelliteFacts(has_foreman=True,
                                              postgresql=SatellitePostgresqlFacts(local_postgresql=True)))
    current_actor_context.run()
    assert mocked_run.commands
    assert len(mocked_run.commands) == 4
    assert mocked_run.commands[0] == ['sed', '-i', '/data_directory/d', '/var/lib/pgsql/data/postgresql.conf']
    assert mocked_run.commands[1] == ['systemctl', 'start', 'postgresql']
    assert mocked_run.commands[2] == ['runuser', '-u', 'postgres', '--', 'reindexdb', '-a']
    assert mocked_run.commands[3] == ['foreman-installer', '--disable-system-checks']
