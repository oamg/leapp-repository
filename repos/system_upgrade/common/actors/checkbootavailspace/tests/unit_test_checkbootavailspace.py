from __future__ import division

import os
from collections import namedtuple

import pytest

from leapp import reporting
from leapp.libraries.actor import checkbootavailspace
from leapp.libraries.actor.checkbootavailspace import (
    check_avail_space_on_boot,
    get_avail_bytes_on_boot,
    inhibit_upgrade,
    MIN_AVAIL_BYTES_FOR_BOOT
)
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api
from leapp.utils.report import is_inhibitor

StatvfsResult = namedtuple('StatvfsResult', ['f_frsize', 'f_bavail'])

LEFTOVER_FILES = {
    '/boot/vmlinuz-upgrade.x86_64': 15 * 2**20,
    '/boot/initramfs-upgrade.x86_64.img': 60 * 2**20,
    '/boot/.vmlinuz-upgrade.x86_64.hmac': 2**10,
}


class fake_get_avail_bytes_on_boot:
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
    assert is_inhibitor(reporting.create_report.report_fields)
    mib_needed = (MIN_AVAIL_BYTES_FOR_BOOT - bytes_available) / 2**20
    assert "needs additional {0} MiB".format(mib_needed) in reporting.create_report.report_fields['summary']


@pytest.mark.parametrize('existing_files', [
    {},
    LEFTOVER_FILES,
    {'/boot/initramfs-upgrade.x86_64.img': 60 * 2**20},
])
def test_get_avail_bytes_on_boot(monkeypatch, existing_files):
    free_bytes = 40 * 2**20
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(checkbootavailspace, 'statvfs', lambda path: StatvfsResult(4096, free_bytes // 4096))
    monkeypatch.setattr(os.path, 'isfile', lambda path: path in existing_files)
    monkeypatch.setattr(os.path, 'getsize', lambda path: existing_files[path])

    assert get_avail_bytes_on_boot() == free_bytes + sum(existing_files.values())


def test_leftover_files_prevent_inhibitor(monkeypatch):
    # 40 MiB free is not enough, but the leftover files from a previous attempt free 75 MiB more
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch='x86_64'))
    monkeypatch.setattr(api, 'current_logger', logger_mocked())
    monkeypatch.setattr(checkbootavailspace, 'statvfs', lambda path: StatvfsResult(4096, (40 * 2**20) // 4096))
    monkeypatch.setattr(os.path, 'isfile', lambda path: path in LEFTOVER_FILES)
    monkeypatch.setattr(os.path, 'getsize', lambda path: LEFTOVER_FILES[path])

    check_avail_space_on_boot(get_avail_bytes_on_boot)

    assert reporting.create_report.called == 0
