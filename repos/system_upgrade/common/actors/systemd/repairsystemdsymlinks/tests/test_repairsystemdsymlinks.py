from leapp.libraries.actor import repairsystemdsymlinks
from leapp.libraries.common import systemd
from leapp.libraries.common.testutils import CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import SystemdServiceFile, SystemdServicesInfoSource


class MockedSystemdCmd(object):
    def __init__(self):
        self.units = []

    def __call__(self, unit, *args, **kwargs):
        self.units.append(unit)
        return {}


def test_bad_symslinks(monkeypatch):
    # there is no _INSTALLATION_CHANGED service on RHEL 8 and RHEL 9, but it's
    # possible such service will be discovered and added in the future as it
    # was on RHEL 7, so let's add such case
    monkeypatch.setitem(
        repairsystemdsymlinks._INSTALLATION_CHANGED,
        "9", ["some.service"],
    )

    service_files = [
        SystemdServiceFile(name='some.service', state='enabled'),
        SystemdServiceFile(name='sysstat.service', state='disabled'),
        SystemdServiceFile(name='hello.service', state='enabled'),
        SystemdServiceFile(name='world.service', state='disabled'),
    ]

    def is_unit_enabled_mocked(unit):
        return True

    monkeypatch.setattr(repairsystemdsymlinks, '_is_unit_enabled', is_unit_enabled_mocked)

    reenable_mocked = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'reenable_unit', reenable_mocked)

    service_info = SystemdServicesInfoSource(service_files=service_files)
    monkeypatch.setattr(
        api,
        "current_actor",
        CurrentActorMocked(src_ver="8.10", dst_ver="9.6", msgs=[service_info]),
    )

    repairsystemdsymlinks._handle_bad_symlinks(service_info.service_files)

    assert reenable_mocked.units == ['some.service']


def test_handle_newly_broken_symlink(monkeypatch):

    symlinks = [
        '/etc/systemd/system/default.target.wants/systemd-readahead-replay.service',
        '/etc/systemd/system/multi-user.target.wants/vdo.service',
        '/etc/systemd/system/multi-user.target.wants/hello.service',
        '/etc/systemd/system/multi-user.target.wants/world.service',
        '/etc/systemd/system/multi-user.target.wants/foo.service',
        '/etc/systemd/system/multi-user.target.wants/bar.service',
    ]

    def is_unit_enabled_mocked(unit):
        return unit in ('hello.service', 'foo.service')

    expect_disabled = [
        'systemd-readahead-replay.service',
        'vdo.service',
        'world.service',
        'bar.service',
    ]

    expect_reenabled = [
        'hello.service',
    ]

    monkeypatch.setattr(repairsystemdsymlinks, '_is_unit_enabled', is_unit_enabled_mocked)

    reenable_mocked = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'reenable_unit', reenable_mocked)

    disable_mocked = MockedSystemdCmd()
    monkeypatch.setattr(systemd, 'disable_unit', disable_mocked)

    service_files = [
        SystemdServiceFile(name='systemd-readahead-replay.service', state='enabled'),
        SystemdServiceFile(name='vdo.service', state='disabled'),
        SystemdServiceFile(name='hello.service', state='enabled'),
        SystemdServiceFile(name='world.service', state='disabled'),
        SystemdServiceFile(name='foo.service', state='disabled'),
        SystemdServiceFile(name='bar.service', state='enabled'),
    ]
    service_info = SystemdServicesInfoSource(service_files=service_files)
    repairsystemdsymlinks._handle_newly_broken_symlinks(symlinks, service_info)

    assert reenable_mocked.units == expect_reenabled
    assert disable_mocked.units == expect_disabled
