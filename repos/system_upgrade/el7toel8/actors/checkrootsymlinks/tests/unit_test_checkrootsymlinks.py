import pytest

from leapp.models import Report, RootDirectory, RootSubdirectory
from leapp.snactor.fixture import current_actor_context


@pytest.mark.parametrize('modified,expected_report', [
    ({}, False),
    ({'bin': '/usr/bin'}, True),
    ({'sbin': 'usr/bin'}, False),
    ({'sbin': '/usr/sbin'}, True),
    ({'lib': '/usr/lib', 'lib64': 'usr/lib64'}, True)])
def test_wrong_symlink_inhibitor(current_actor_context, modified, expected_report):
    subdirs = {
        'bin': 'usr/bin',
        'boot': '',
        'dev': '',
        'etc': '',
        'home': '',
        'lib': 'usr/lib',
        'lib64': 'usr/lib64',
        'media': '',
        'mnt': '',
        'opt': '',
        'proc': '',
        'root': '',
        'run': '',
        'sbin': 'usr/sbin',
        'srv': '',
        'sys': '',
        'tmp': '',
        'usr': '',
        'var': ''
    }
    subdirs.update(modified)
    items = [RootSubdirectory(name=subdir, target=subdirs[subdir]) for subdir in subdirs]
    current_actor_context.feed(RootDirectory(items=items))
    current_actor_context.run()
    if expected_report:
        assert current_actor_context.consume(Report)
    else:
        assert not current_actor_context.consume(Report)
