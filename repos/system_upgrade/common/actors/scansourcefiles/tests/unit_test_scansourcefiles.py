import os

import pytest

from leapp.libraries.actor import scansourcefiles
from leapp.libraries.common import testutils
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import FileInfo, TrackedFilesInfoSource


@pytest.mark.parametrize(
    ('run_output', 'expected_output_is_modified'),
    (
        ({'exit_code': 0}, False),
        ({'exit_code': 1, 'stdout': 'missing     /boot/efi/EFI (Permission denied)'}, True),
        ({'exit_code': 1, 'stdout': 'S.5......  c /etc/openldap/ldap.conf'}, True),
        ({'exit_code': 1, 'stdout': '..?......  c /etc/libaudit.conf'}, False),
        ({'exit_code': 1, 'stdout': '.....UG..  g /var/run/avahi-daemon'}, False),
    )
)
def test_is_modified(monkeypatch, run_output, expected_output_is_modified):
    input_file = '/file'

    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-Vf', '--nomtime', input_file]
        return run_output

    monkeypatch.setattr(scansourcefiles, 'run', mocked_run)
    assert scansourcefiles.is_modified(input_file) == expected_output_is_modified


@pytest.mark.parametrize(
    'run_output',
    [
        {'stdout': ['']},
        {'stdout': ['rpm']},
        {'stdout': ['rpm1', 'rpm2']},
    ]
)
def test_get_rpm_name(monkeypatch, run_output):
    input_file = '/file'

    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-qf', '--queryformat', r'%{NAME}\n', input_file]
        return run_output

    monkeypatch.setattr(scansourcefiles, 'run', mocked_run)
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())
    assert scansourcefiles._get_rpm_name(input_file) == run_output['stdout'][0]

    if len(run_output['stdout']) > 1:
        expected_warnmsg = ('The {} file is owned by multiple rpms: {}.'
                            .format(input_file, ', '.join(run_output['stdout'])))
        assert api.current_logger.warnmsg == [expected_warnmsg]


def test_get_rpm_name_error(monkeypatch):
    input_file = '/file'

    def mocked_run(cmd, *args, **kwargs):
        assert cmd == ['rpm', '-qf', '--queryformat', r'%{NAME}\n', input_file]
        raise CalledProcessError("mocked error", cmd, "result")

    monkeypatch.setattr(scansourcefiles, 'run', mocked_run)
    assert scansourcefiles._get_rpm_name(input_file) == ''


@pytest.mark.parametrize(
    ('input_file', 'exists', 'rpm_name', 'is_modified'),
    (
        ('/not_existing_file', False, '', False),
        ('/not_existing_file_rpm_owned', False, 'rpm', False),
        ('/not_existing_file_rpm_owned_modified', False, 'rpm', True),
        ('/existing_file_not_modified', True, '', False),
        ('/existing_file_owned_by_rpm_not_modified', True, 'rpm', False),
        ('/existing_file_owned_by_rpm_modified', True, 'rpm', True),
    )
)
def test_scan_file(monkeypatch, input_file, exists, rpm_name, is_modified):
    monkeypatch.setattr(scansourcefiles, 'is_modified', lambda _: is_modified)
    monkeypatch.setattr(scansourcefiles, '_get_rpm_name', lambda _: rpm_name)
    monkeypatch.setattr(os.path, 'exists', lambda _: exists)

    expected_model_output = FileInfo(path=input_file, exists=exists, rpm_name=rpm_name, is_modified=is_modified)
    assert scansourcefiles.scan_file(input_file) == expected_model_output


@pytest.mark.parametrize(
    ('input_files'),
    (
        ([]),
        (['/file1']),
        (['/file1', '/file2']),
    )
)
def test_scan_files(monkeypatch, input_files):
    base_data = {
        'exists': False,
        'rpm_name': '',
        'is_modified': False
    }

    def scan_file_mocked(input_file):
        return FileInfo(path=input_file, **base_data)

    monkeypatch.setattr(scansourcefiles, 'scan_file', scan_file_mocked)
    expected_output_list = [FileInfo(path=input_file, **base_data) for input_file in input_files]
    assert scansourcefiles.scan_files(input_files) == expected_output_list


@pytest.mark.parametrize(
    'rhel_major_version', ['8', '9']
)
def test_tracked_files(monkeypatch, rhel_major_version):
    TRACKED_FILES_MOCKED = {
        'common': [
            '/file1',
        ],
        '8': [
            '/file2',
        ],
        '9': [
            '/file3',
        ],
    }

    def scan_files_mocked(files):
        return [FileInfo(path=file_path, exists=False, rpm_name='', is_modified=False) for file_path in files]

    monkeypatch.setattr(api, 'produce', testutils.produce_mocked())
    monkeypatch.setattr(scansourcefiles, 'TRACKED_FILES', TRACKED_FILES_MOCKED)
    monkeypatch.setattr(scansourcefiles, 'get_source_major_version', lambda: rhel_major_version)
    monkeypatch.setattr(scansourcefiles, 'scan_files', scan_files_mocked)

    scansourcefiles.process()

    tracked_files_model = api.produce.model_instances[0]
    assert api.produce.called == 1
    assert isinstance(tracked_files_model, TrackedFilesInfoSource)
    # assert only 1 common and 1 version file were scanned
    assert len(tracked_files_model.files) == 2
    assert all(isinstance(files_list_item, FileInfo) for files_list_item in tracked_files_model.files)
