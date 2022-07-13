from leapp.models import CephInfo, LsblkEntry, StorageInfo
from leapp.reporting import Report
from leapp.snactor.fixture import current_actor_context
from leapp.utils.report import is_inhibitor


def test_actor_with_luks(current_actor_context):
    with_luks = [LsblkEntry(name='luks-132', kname='kname1', maj_min='253:0', rm='0',
                            size='10G', bsize=10*(1 << 39), ro='0', tp='crypt', mountpoint='')]

    current_actor_context.feed(StorageInfo(lsblk=with_luks))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    report_fields = current_actor_context.consume(Report)[0].report
    assert is_inhibitor(report_fields)


def test_actor_with_luks_ceph_only(current_actor_context):
    with_luks = [LsblkEntry(name='luks-132', kname='kname1', maj_min='253:0', rm='0',
                            size='10G', bsize=10*(1 << 39), ro='0', tp='crypt', mountpoint='')]
    ceph_volume = ['luks-132']
    current_actor_context.feed(StorageInfo(lsblk=with_luks))
    current_actor_context.feed(CephInfo(encrypted_volumes=ceph_volume))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)


def test_actor_without_luks(current_actor_context):
    without_luks = [LsblkEntry(name='sda1', kname='sda1', maj_min='8:0', rm='0',
                               size='10G', bsize=10*(1 << 39), ro='0', tp='part', mountpoint='/boot')]

    current_actor_context.feed(StorageInfo(lsblk=without_luks))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
