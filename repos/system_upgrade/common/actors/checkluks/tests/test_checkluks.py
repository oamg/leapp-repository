from leapp.libraries.actor import checkluks
from leapp.libraries.common import distro
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import (
    CephInfo,
    KernelCmdline,
    KernelCmdlineArg,
    LsblkEntry,
    LuksDump,
    LuksDumps,
    LuksToken,
    TargetKernelCmdlineArgTasks,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor

_REPORT_TITLE_UNSUITABLE = 'Detected LUKS devices unsuitable for in-place upgrade.'


def test_actor_with_luks1_notpm(monkeypatch, current_actor_context):
    monkeypatch.setattr(checkluks, 'get_source_major_version', lambda: '8')
    monkeypatch.setattr(distro, 'get_source_distro_id', lambda: 'rhel')
    monkeypatch.setattr(distro, 'get_target_distro_id', lambda: 'rhel')

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
    monkeypatch.setattr(checkluks, 'get_source_major_version', lambda: '8')
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
    monkeypatch.setattr(checkluks, 'get_source_major_version', lambda: '8')
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
    monkeypatch.setattr(checkluks, 'get_source_major_version', lambda: '8')
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
    monkeypatch.setattr(checkluks, 'get_source_major_version', lambda: '8')
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


def test_rdluks_uuid_args_removed_from_upgrade_cmdline(monkeypatch):
    cmdline = KernelCmdline(parameters=[
        KernelCmdlineArg(key='root', value='/dev/mapper/rhel-root'),
        KernelCmdlineArg(key='rd.luks.uuid', value='luks-aaa-bbb'),
        KernelCmdlineArg(key='rd.luks.uuid', value='luks-ccc-ddd'),
        KernelCmdlineArg(key='ro', value=None),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkluks._emit_rdluks_undesired_for_upgrade_cmdline()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert len(upgrade_msgs) == 1

    removed_keys_values = {(arg.key, arg.value) for arg in upgrade_msgs[0].to_remove}
    assert removed_keys_values == {
        ('rd.luks.uuid', 'luks-aaa-bbb'),
        ('rd.luks.uuid', 'luks-ccc-ddd'),
    }

    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert len(target_msgs) == 1

    readded_keys_values = {(arg.key, arg.value) for arg in target_msgs[0].to_add}
    assert readded_keys_values == {
        ('rd.luks.uuid', 'luks-aaa-bbb'),
        ('rd.luks.uuid', 'luks-ccc-ddd'),
    }


def test_no_rdluks_uuid_no_message(monkeypatch):
    cmdline = KernelCmdline(parameters=[
        KernelCmdlineArg(key='root', value='/dev/mapper/rhel-root'),
        KernelCmdlineArg(key='ro', value=None),
    ])
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[cmdline]))
    monkeypatch.setattr(api, 'produce', produce_mocked())

    checkluks._emit_rdluks_undesired_for_upgrade_cmdline()

    upgrade_msgs = [m for m in api.produce.model_instances if isinstance(m, UpgradeKernelCmdlineArgTasks)]
    assert not upgrade_msgs
    target_msgs = [m for m in api.produce.model_instances if isinstance(m, TargetKernelCmdlineArgTasks)]
    assert not target_msgs
