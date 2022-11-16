import pytest

from leapp.libraries import stdlib
from leapp.libraries.actor import setsystemdservicesstate
from leapp.libraries.common import systemd
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import SystemdServicesTasks


class MockedSystemdCmd(object):
    def __init__(self):
        self.units = []

    def __call__(self, unit, *args, **kwargs):
        self.units.append(unit)
        return {}


@pytest.mark.parametrize(
    ('msgs', 'expect_enable_units', 'expect_disable_units'),
    [
        (
            [SystemdServicesTasks(to_enable=['hello.service'],
                                  to_disable=['getty.service'])],
            ['hello.service'],
            ['getty.service']
        ),
        (
            [SystemdServicesTasks(to_disable=['getty.service'])],
            [],
            ['getty.service']
        ),
        (
            [SystemdServicesTasks(to_enable=['hello.service'])],
            ['hello.service'],
            []
        ),
        (
            [SystemdServicesTasks()],
            [],
            []
        ),
    ]
)
def test_process(monkeypatch, msgs, expect_enable_units, expect_disable_units):
    mocked_enable = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'enable_unit', mocked_enable)

    mocked_disable = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'disable_unit', mocked_disable)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))

    setsystemdservicesstate.process()

    assert mocked_enable.units == expect_enable_units
    assert mocked_disable.units == expect_disable_units


def test_process_invalid(monkeypatch):

    def mocked_run(cmd, *args, **kwargs):
        if cmd == ['systemctl', 'enable', 'invalid.service']:
            message = 'Command {0} failed with exit code {1}.'.format(str(cmd), 1)
            raise CalledProcessError(message, cmd, 1)

    msgs = [SystemdServicesTasks(to_enable=['invalid.service'])]

    monkeypatch.setattr(systemd, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    setsystemdservicesstate.process()

    expect_msg = ("Failed to enable systemd unit \"invalid.service\". Message:"
                  " Command ['systemctl', 'enable', 'invalid.service'] failed with exit code 1.")
    assert expect_msg in api.current_logger.errmsg


def test_enable_disable_conflict_logged(monkeypatch):
    msgs = [SystemdServicesTasks(to_enable=['hello.service'], to_disable=['hello.service'])]

    mocked_enable = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'enable_unit', mocked_enable)

    mocked_disable = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'disable_unit', mocked_disable)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=msgs))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    setsystemdservicesstate.process()

    expect_msg = ('Attempted to both enable and disable systemd service "hello.service",'
                  ' service will be disabled.')
    assert expect_msg in api.current_logger.errmsg
