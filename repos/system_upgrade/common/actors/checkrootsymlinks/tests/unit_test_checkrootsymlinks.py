import pytest
import six

from leapp.models import InvalidRootSubdirectory, Report, RootDirectory, RootSubdirectory
from leapp.snactor.fixture import current_actor_context


@pytest.mark.parametrize('modified,invalid,expected_report', [
    ({}, {}, False),
    ({'bin': '/usr/bin'}, {}, True),
    ({'sbin': 'usr/bin'}, {}, False),
    ({'sbin': '/usr/sbin'}, {}, True),
    ({'lib': '/usr/lib', 'lib64': 'usr/lib64'}, {}, True),
    ({}, {b'\xc4\xc9\xd2\xc5\xcb\xd4\xcf\xd2\xc9\xd1': b''}, False),
    ({}, {b'\xc4\xc9\xd2\xc5\xcb\xd4\xcf\xd2\xc9\xd1': b'usr/bin'}, False),
    ({'lib': '/usr/lib', 'lib64': 'usr/lib64'}, {b'\xc4\xc9\xd2\xc5\xcb\xd4\xcf\xd2\xc9\xd1': b'/usr/lib64'}, True),
    ({}, {b'\xc4\xc9\xd2\xc5\xcb\xd4\xcf\xd2\xc9\xd1': b'/usr/lib64'}, True)])
def test_wrong_symlink_inhibitor(current_actor_context, modified, invalid, expected_report):
    invalid_subdirs = {}
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
    invalid_subdirs.update(invalid)

    items = [RootSubdirectory(name=name, target=target) for name, target in subdirs.items()]
    invalid_items = [InvalidRootSubdirectory(name=name, target=target) for name, target in invalid_subdirs.items()]
    current_actor_context.feed(RootDirectory(items=items, invalid_items=invalid_items))
    current_actor_context.run()
    if expected_report:
        report = current_actor_context.consume(Report)
        assert report
        # Make sure the hint is there in case of non-utf bad symlinks
        if invalid_subdirs:
            msg = 'symbolic links point to absolute paths that have non-utf8 encoding'
            hint = next((rem['context'] for rem in report[0].report['detail']['remediations']
                         if rem['type'] == 'hint'), None)
            assert msg in hint
    else:
        assert not current_actor_context.consume(Report)
