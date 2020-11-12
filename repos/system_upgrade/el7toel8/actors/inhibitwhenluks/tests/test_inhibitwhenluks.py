from leapp.snactor.fixture import current_actor_context
from leapp.models import StorageInfo, LsblkEntry
from leapp.reporting import Report


def test_actor_with_luks(current_actor_context):
    with_luks = [LsblkEntry(name='luks-132', maj_min='253:0', rm='0',
                            size='10G', ro='0', tp='crypt', mountpoint=''
                            )]

    current_actor_context.feed(StorageInfo(lsblk=with_luks))
    current_actor_context.run()
    assert current_actor_context.consume(Report)
    report_fields = current_actor_context.consume(Report)[0].report
    assert 'inhibitor' in report_fields['groups']


def test_actor_without_luks(current_actor_context):
    without_luks = [LsblkEntry(name='sda1', maj_min='8:0', rm='0',
                               size='10G', ro='0', tp='part', mountpoint='/boot'
                               )]

    current_actor_context.feed(StorageInfo(lsblk=without_luks))
    current_actor_context.run()
    assert not current_actor_context.consume(Report)
