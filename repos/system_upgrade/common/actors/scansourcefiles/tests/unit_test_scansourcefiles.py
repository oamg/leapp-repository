import os

import pytest

from leapp.libraries.actor import scansourcefiles
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api
from leapp.models import FileInfo, TrackedFilesInfoSource

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(CUR_DIR, 'files')

# values in list should correspond with the return values of get_source_major_version()
RHEL_MAJOR_VERSIONS_LIST = list(range(8, 9+1))

TRACKED_FILES_BY_VERSIONS = {
    version: ['{}/file_major_version_{}'.format(FILES_DIR, version)]
    for version in RHEL_MAJOR_VERSIONS_LIST
    }

VERSION_FILES_MOCKED = {
    'common': [
        '{}/file_not_rpm_owned'.format(FILES_DIR),
    ]
}

VERSION_FILES_MOCKED.update(TRACKED_FILES_BY_VERSIONS)


@pytest.mark.parametrize('major_version', RHEL_MAJOR_VERSIONS_LIST)
def test_version_files_with_common(monkeypatch, major_version):
    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: major_version)
    monkeypatch.setattr(scansourcefiles, 'TRACKED_FILES', VERSION_FILES_MOCKED)
    scansourcefiles.process()

    assert api.produce.called == 1
    assert isinstance(api.produce.model_instances[0], TrackedFilesInfoSource)
    # assert only files from correct major version were scanned, so common files + 1 (version file)
    assert len(api.produce.model_instances[0].files) == len(VERSION_FILES_MOCKED['common']) + 1

    assert isinstance(api.produce.model_instances[0].files[0], FileInfo)
    assert api.produce.model_instances[0].files[0].path == '{}/file_not_rpm_owned'.format(FILES_DIR)
    assert api.produce.model_instances[0].files[0].exists is True
    assert api.produce.model_instances[0].files[0].rpm_name == ''
    assert api.produce.model_instances[0].files[0].is_modified is False

    INDEX_OF_VERSION_FILE = len(VERSION_FILES_MOCKED['common'])
    assert isinstance(api.produce.model_instances[0].files[INDEX_OF_VERSION_FILE], FileInfo)
    version_file_path = '{}/file_major_version_{}'.format(FILES_DIR, major_version)
    assert api.produce.model_instances[0].files[INDEX_OF_VERSION_FILE].path == version_file_path
    assert api.produce.model_instances[0].files[INDEX_OF_VERSION_FILE].exists is False
    assert api.produce.model_instances[0].files[INDEX_OF_VERSION_FILE].rpm_name == ''
    assert api.produce.model_instances[0].files[INDEX_OF_VERSION_FILE].is_modified is False

    assert not api.current_logger.errmsg


def test_modified_rpm_owned_files(monkeypatch):

    class run_mocked(object):

        def __init__(self):
            self.called = 0

        def __call__(self, args, **kwargs):
            self.called += 1
            # run to check if file is owned by rpm
            if '-qf' in args:
                if '{}/file_rpm_owned'.format(FILES_DIR) in args:
                    return {'stdout': ['rpm']}
                if '{}/file_owned_by_multiple_rpms'.format(FILES_DIR) in args:
                    return {'stdout': ['rpm1', 'rpm2']}
                return {'stdout': []}
            # run to check if file was modified
            if '-Vf' in args:
                return {'exit_code': 0}
            return {'exit_code': 1, 'stdout': []}

    FILES_MOCKED = {
        'common': [
            '{}/file_rpm_owned'.format(FILES_DIR),
            '{}/file_owned_by_multiple_rpms'.format(FILES_DIR),
        ],
    }

    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: 9)
    monkeypatch.setattr(scansourcefiles, 'run', run_mocked())
    monkeypatch.setattr(scansourcefiles, 'is_modified', lambda x: True)
    monkeypatch.setattr(scansourcefiles, 'TRACKED_FILES', FILES_MOCKED)

    scansourcefiles.process()

    assert isinstance(api.produce.model_instances[0].files[0], FileInfo)
    assert api.produce.model_instances[0].files[0].path == '{}/file_rpm_owned'.format(FILES_DIR)
    assert api.produce.model_instances[0].files[0].exists is True
    assert api.produce.model_instances[0].files[0].rpm_name == 'rpm'
    assert api.produce.model_instances[0].files[0].is_modified is True

    assert isinstance(api.produce.model_instances[0].files[1], FileInfo)
    assert api.produce.model_instances[0].files[1].path == '{}/file_owned_by_multiple_rpms'.format(FILES_DIR)
    assert api.produce.model_instances[0].files[1].exists is True
    assert api.produce.model_instances[0].files[1].rpm_name == 'rpm1'
    assert api.produce.model_instances[0].files[1].is_modified is True

    assert len(api.current_logger.warnmsg) == 1
    log_msg = 'The {}/file_owned_by_multiple_rpms file is owned by multiple rpms: rpm1, rpm2.'.format(FILES_DIR)
    assert api.current_logger.warnmsg[0] == log_msg


def test_non_existent_file(monkeypatch):
    FILES_MOCKED = {'common': ['{}/file_nonexistent'.format(FILES_DIR)]}

    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: 9)
    monkeypatch.setattr(scansourcefiles, 'TRACKED_FILES', FILES_MOCKED)

    scansourcefiles.process()

    assert isinstance(api.produce.model_instances[0].files[0], FileInfo)
    assert api.produce.model_instances[0].files[0].path == '{}/file_nonexistent'.format(FILES_DIR)
    assert api.produce.model_instances[0].files[0].exists is False
    assert api.produce.model_instances[0].files[0].rpm_name == ''
    assert api.produce.model_instances[0].files[0].is_modified is False

    assert not api.current_logger.warnmsg
