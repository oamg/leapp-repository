import os

import pytest

from leapp.libraries.actor import scansourcefiles
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FileInfo, TrackedFilesInfoSource

# values in list should correspond with the return values of get_source_major_version()
RHEL_MAJOR_VERSIONS_LIST = list(range(8, 9+1))

TRACKED_FILES_BY_VERSIONS = {
    version: ['/file_major_version_{}'.format(version)]
    for version in RHEL_MAJOR_VERSIONS_LIST
    }

TRACKED_FILES_MOCKED = {
    'common': [
        '/file'
    ]
}

TRACKED_FILES_MOCKED.update(TRACKED_FILES_BY_VERSIONS)


@pytest.mark.parametrize('run_output,expected_output', (
    ({'exit_code': 0}, False),
    ({'exit_code': 1, 'stdout': 'missing     /boot/efi/EFI (Permission denied)'}, True),
    ({'exit_code': 1, 'stdout': 'S.5......  c /etc/openldap/ldap.conf'}, True),
    ({'exit_code': 1, 'stdout': '..?......  c /etc/libaudit.conf'}, False),
    ({'exit_code': 1, 'stdout': '.....UG..  g /var/run/avahi-daemon'}, False),
))
def test_is_modified(monkeypatch, run_output, expected_output):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-Vf', '--nomtime', input_file]
        return run_output

    input_file = '/file'
    monkeypatch.setattr(scansourcefiles, 'run', mocked_run)

    assert scansourcefiles.is_modified(input_file) == expected_output


@pytest.mark.parametrize('run_output,expected_output', (
    ({'stdout': ['rpm']}, 'rpm'),
    ({'stdout': ['rpm1', 'rpm2']}, 'rpm1'),
    (CalledProcessError, ''),
))
def test_get_rpm_name(monkeypatch, run_output, expected_output):
    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-qf', '--queryformat', r'%{NAME}\n', input_file]
        if raise_error:
            raise CalledProcessError("mocked error", cmd, "result")
        return run_output

    raise_error = run_output and not isinstance(run_output, dict)
    input_file = '/file'

    monkeypatch.setattr(scansourcefiles, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())

    assert scansourcefiles._get_rpm_name(input_file) == expected_output

    if raise_error:
        return

    if len(run_output['stdout']) > 1:
        assert len(api.current_logger.warnmsg) == 1
        expected_warnmsg = 'The {} file is owned by multiple rpms: rpm1, rpm2.'.format(input_file)
        assert api.current_logger.warnmsg[0] == expected_warnmsg
    else:
        assert not api.current_logger.warnmsg


@pytest.mark.parametrize('input_file,rpm_name,exists,modified,expected_output', (
    ('/file1', 'rpm', False, True,
     FileInfo(path='/file1', exists=False, rpm_name='rpm', is_modified=True)),

    ('/file2', '', True, False,
     FileInfo(path='/file2', exists=True, rpm_name='', is_modified=False))
))
def test_scan_file(monkeypatch, input_file, rpm_name, modified, exists, expected_output):
    monkeypatch.setattr(scansourcefiles, 'is_modified', lambda _: modified)
    monkeypatch.setattr(scansourcefiles, '_get_rpm_name', lambda _: rpm_name)
    monkeypatch.setattr(os.path, 'exists', lambda _: exists)

    file_info = scansourcefiles.scan_file(input_file)

    assert isinstance(file_info, FileInfo)
    assert file_info == expected_output


@pytest.mark.parametrize('input_files,rpm_name,exists,modified,expected_output', (
    ([], '', False, False, []),

    (['/file1'], '', False, False,
     [FileInfo(path='/file1', exists=False, rpm_name='', is_modified=False)]),

    (['/file1', '/file2'], '', False, False,
     [FileInfo(path='/file1', exists=False, rpm_name='', is_modified=False),
      FileInfo(path='/file2', exists=False, rpm_name='', is_modified=False)]),

    (['/file_rpm_modified'], 'rpm', False, True,
     [FileInfo(path='/file_rpm_modified', exists=False, rpm_name='rpm', is_modified=True)]),

    (['/file_rpm_not_modified'], 'rpm', False, False,
     [FileInfo(path='/file_rpm_not_modified', exists=False, rpm_name='rpm', is_modified=False)]),
))
def test_scan_files(monkeypatch, input_files, rpm_name, exists, modified, expected_output):
    def scan_file_mocked(input_file):
        return FileInfo(path=input_file, exists=exists, rpm_name=rpm_name, is_modified=modified)

    monkeypatch.setattr(scansourcefiles, 'scan_file', scan_file_mocked)

    assert scansourcefiles.scan_files(input_files) == expected_output


@pytest.mark.parametrize('input_file,rpm_name,exists,modified,expected_output', (
    ('/file_rpm_not_modified', 'rpm', False, False,
     FileInfo(path='/file_rpm_not_modified', exists=False, rpm_name='rpm', is_modified=False)),

    ('/file_rpm_modified', 'rpm', False, True,
     FileInfo(path='/file_rpm_modified', exists=False, rpm_name='rpm', is_modified=True)),
))
def test_rpm_owned_files(monkeypatch, input_file, rpm_name, exists, modified, expected_output):
    def scan_files_mocked(*args, **kwargs):
        return [FileInfo(path=input_file, exists=exists, rpm_name=rpm_name, is_modified=modified)]

    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: 9)
    monkeypatch.setattr(scansourcefiles, 'scan_files', scan_files_mocked)

    scansourcefiles.process()

    tracked_files = api.produce.model_instances[0]
    assert isinstance(tracked_files, TrackedFilesInfoSource)
    file_info = tracked_files.files[0]
    assert isinstance(file_info, FileInfo)

    assert api.produce.called == 1
    assert len(tracked_files.files) == 1
    assert file_info == expected_output


@pytest.mark.parametrize(
    'major_version,version_file_expected_output,common_file_expected_output',
    [(major_version,
      FileInfo(path='/file_major_version_{}'.format(major_version), exists=False, rpm_name='', is_modified=False),
      FileInfo(path='/file', exists=False, rpm_name='', is_modified=False))
     for major_version in RHEL_MAJOR_VERSIONS_LIST]
)
def test_version_file_with_common_file(monkeypatch, major_version,
                                       version_file_expected_output, common_file_expected_output):
    def scan_files_mocked(*args, **kwargs):
        files = TRACKED_FILES_MOCKED['common'] + TRACKED_FILES_MOCKED.get(major_version, [])
        return [FileInfo(path=file_, exists=False, rpm_name='', is_modified=False) for file_ in files]

    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: major_version)
    monkeypatch.setattr(scansourcefiles, 'scan_files', scan_files_mocked)

    scansourcefiles.process()

    tracked_files = api.produce.model_instances[0]
    assert api.produce.called == 1
    assert isinstance(tracked_files, TrackedFilesInfoSource)
    # assert only 1 common and 1 version file were scanned
    assert len(tracked_files.files) == 2

    file1 = tracked_files.files[0]
    assert file1 == common_file_expected_output
    file2 = tracked_files.files[1]
    assert file2 == version_file_expected_output
