from __future__ import division

from leapp import reporting
from leapp.libraries.actor.checkbootavailspace import (
    MIN_AVAIL_BYTES_FOR_BOOT,
    check_avail_space_on_boot,
    inhibit_upgrade,
)
from leapp.libraries.common.testutils import create_report_mocked


class fake_get_avail_bytes_on_boot(object):
    def __init__(self, size):
        self.size = size

    def __call__(self, *args):
        return self.size


def test_not_enough_space_available(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    # Test 0 bytes available /boot
    get_avail_bytes_on_boot = fake_get_avail_bytes_on_boot(0)
    check_avail_space_on_boot(get_avail_bytes_on_boot)

    # Test 0.1 MiB less then required in /boot
    get_avail_bytes_on_boot = fake_get_avail_bytes_on_boot(MIN_AVAIL_BYTES_FOR_BOOT - 0.1 * 2**20)
    check_avail_space_on_boot(get_avail_bytes_on_boot)

    assert reporting.create_report.called == 2


def test_enough_space_available(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    get_avail_bytes_on_boot = fake_get_avail_bytes_on_boot(MIN_AVAIL_BYTES_FOR_BOOT)
    check_avail_space_on_boot(get_avail_bytes_on_boot)

    assert reporting.create_report.called == 0


def test_inhibit_upgrade(monkeypatch):
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    # Test 4.2 MiB available on /boot
    bytes_available = 4.2 * 2**20
    inhibit_upgrade(bytes_available)

    assert reporting.create_report.called == 1
    assert 'inhibitor' in reporting.create_report.report_fields['groups']
    mib_needed = (MIN_AVAIL_BYTES_FOR_BOOT - bytes_available) / 2**20
    assert "needs additional {0} MiB".format(mib_needed) in reporting.create_report.report_fields['summary']
