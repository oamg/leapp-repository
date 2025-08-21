from leapp.libraries.common.config import version
from leapp.models import (
    CephInfo,
    LsblkEntry,
    LuksDump,
    LuksDumps,
    LuksToken,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks
)
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor

_REPORT_TITLE_UNSUITABLE = 'Detected LUKS devices unsuitable for in-place upgrade.'


def test_actor_with_luks1_notpm(monkeypatch, current_actor_context):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: '8')
    luks_dump = LuksDump(
        version=1,
        uuid='dd09e6d4-b595-4f1c-80b8-fd47540e6464',
        device_path='/dev/sda',
        device_name='sda')
    current_actor_context.feed(LuksDumps(dumps=[luks_dump]))
    current_actor_context.feed(CephInfo(encrypted_volumes=[]))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert not current_actor_context.consume(TargetUserSpaceUpgradeTasks)
    assert not current_actor_context.consume(UpgradeInitramfsTasks)

    assert report_fields['title'] == _REPORT_TITLE_UNSUITABLE
    assert 'LUKS1 partitions have been discovered' in report_fields['summary']
    assert luks_dump.device_name in report_fields['summary']


def test_actor_with_luks2_notpm(monkeypatch, current_actor_context):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: '8')
    luks_dump = LuksDump(
        version=2,
        uuid='27b57c75-9adf-4744-ab04-9eb99726a301',
        device_path='/dev/sda',
        device_name='sda')
    current_actor_context.feed(LuksDumps(dumps=[luks_dump]))
    current_actor_context.feed(CephInfo(encrypted_volumes=[]))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)
    assert not current_actor_context.consume(TargetUserSpaceUpgradeTasks)
    assert not current_actor_context.consume(UpgradeInitramfsTasks)

    assert report_fields['title'] == _REPORT_TITLE_UNSUITABLE
    assert 'LUKS2 devices without Clevis TPM2 token' in report_fields['summary']
    assert luks_dump.device_name in report_fields['summary']


def test_actor_with_luks2_invalid_token(monkeypatch, current_actor_context):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: '8')
    luks_dump = LuksDump(
        version=2,
        uuid='dc1dbe37-6644-4094-9839-8fc5dcbec0c6',
        device_path='/dev/sda',
        device_name='sda',
        tokens=[LuksToken(token_id=0, keyslot=1, token_type='clevis')])
    current_actor_context.feed(LuksDumps(dumps=[luks_dump]))
    current_actor_context.feed(CephInfo(encrypted_volumes=[]))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)

    assert report_fields['title'] == _REPORT_TITLE_UNSUITABLE
    assert 'LUKS2 devices without Clevis TPM2 token' in report_fields['summary']
    assert luks_dump.device_name in report_fields['summary']
    assert not current_actor_context.consume(TargetUserSpaceUpgradeTasks)
    assert not current_actor_context.consume(UpgradeInitramfsTasks)


def test_actor_with_luks2_clevis_tpm_token(monkeypatch, current_actor_context):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: '8')
    luks_dump = LuksDump(
        version=2,
        uuid='83050bd9-61c6-4ff0-846f-bfd3ac9bfc67',
        device_path='/dev/sda',
        device_name='sda',
        tokens=[LuksToken(token_id=0, keyslot=1, token_type='clevis-tpm2')])
    current_actor_context.feed(LuksDumps(dumps=[luks_dump]))
    current_actor_context.feed(CephInfo(encrypted_volumes=[]))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)

    upgrade_tasks = current_actor_context.consume(TargetUserSpaceUpgradeTasks)
    assert len(upgrade_tasks) == 1
    assert set(upgrade_tasks[0].install_rpms) == set([
                'clevis',
                'clevis-dracut',
                'clevis-systemd',
                'clevis-udisks2',
                'clevis-luks',
                'cryptsetup',
                'tpm2-tss',
                'tpm2-tools',
                'tpm2-abrmd'
            ])
    assert current_actor_context.consume(UpgradeInitramfsTasks)


def test_actor_with_luks2_ceph(monkeypatch, current_actor_context):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: '8')
    ceph_volume = ['sda']
    current_actor_context.feed(CephInfo(encrypted_volumes=ceph_volume))
    luks_dump = LuksDump(
        version=2,
        uuid='0edb8c11-1a04-4abd-a12d-93433ee7b8d8',
        device_path='/dev/sda',
        device_name='sda',
        tokens=[LuksToken(token_id=0, keyslot=1, token_type='clevis')])
    current_actor_context.feed(LuksDumps(dumps=[luks_dump]))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)

    # make sure we don't needlessly include clevis packages, when there is no clevis token
    assert not current_actor_context.consume(TargetUserSpaceUpgradeTasks)


LSBLK_ENTRY = LsblkEntry(
    name="luks-whatever",
    kname="dm-0",
    maj_min="252:1",
    rm="0",
    size="1G",
    bsize=1073741824,
    ro="0",
    tp="crypt",
    mountpoint="/",
    parent_name="",
    parent_path=""
)
