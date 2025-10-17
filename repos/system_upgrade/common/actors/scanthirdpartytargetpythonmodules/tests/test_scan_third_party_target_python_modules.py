from collections import defaultdict, namedtuple
from pathlib import Path

import pytest

from leapp.libraries.actor import scanthirdpartytargetpythonmodules
from leapp.libraries.common.testutils import logger_mocked
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

Parent = namedtuple('Parent', ['name'])
MockFile = namedtuple('MockFile', ['name', 'parent', 'path'])


def _mock_file_str(self):
    return self.path


MockFile.__str__ = _mock_file_str


@pytest.mark.parametrize('rhel_version,expected_python', [
    ('9', 'python3.9'),
    ('10', 'python3.12'),
    ('8', None),
    ('7', None),
    ('', None),
    ('invalid', None),
    (None, None),
])
def test_get_python_binary_for_rhel(rhel_version, expected_python):
    assert scanthirdpartytargetpythonmodules.get_python_binary_for_rhel(rhel_version) == expected_python


@pytest.mark.parametrize('file_name,parent_name,should_skip', [
    ('module.pyc', '__pycache__', True),
    ('module.pyc', 'site-packages', False),
    ('module.py', '__pycache__', False),
    ('module.so', '__pycache__', False),
    ('module.py', 'site-packages', False),
    ('module.so', 'site-packages', False),
])
def test_should_skip_file(file_name, parent_name, should_skip):
    mock_file = MockFile(name=file_name, parent=Parent(name=parent_name), path='/dummy/path')
    assert scanthirdpartytargetpythonmodules._should_skip_file(mock_file) is should_skip


def test_scan_python_files(monkeypatch):
    system_paths = [Path('/usr/lib/python3.9/site-packages')]
    rpm_files = {
        '/usr/lib/python3.9/site-packages/rpm_module.py': 'rpm-package',
        '/usr/lib/python3.9/site-packages/another.py': 'another-rpm',
    }

    def mock_is_dir(self):
        return True

    def mock_find_python_related(root):
        files = [
            MockFile('rpm_module.py', Parent('site-packages'), '/usr/lib/python3.9/site-packages/rpm_module.py'),
            MockFile('unowned.py', Parent('site-packages'), '/usr/lib/python3.9/site-packages/unowned.py'),
            MockFile('another.py', Parent('site-packages'), '/usr/lib/python3.9/site-packages/another.py'),
        ]
        return iter(files)

    monkeypatch.setattr(Path, 'is_dir', mock_is_dir)
    monkeypatch.setattr(scanthirdpartytargetpythonmodules, 'find_python_related', mock_find_python_related)

    rpms_to_check, unowned = scanthirdpartytargetpythonmodules.scan_python_files(system_paths, rpm_files)

    assert 'rpm-package' in rpms_to_check
    assert 'another-rpm' in rpms_to_check
    assert '/usr/lib/python3.9/site-packages/unowned.py' in unowned
    assert len(unowned) == 1


@pytest.mark.parametrize('path_exists,mock_files', [
    (False, None),
    (True, [MockFile('module.pyc', Parent('__pycache__'), '/usr/lib/python3.9/site-packages/__pycache__/module.pyc')]),
])
def test_scan_python_files_filtering(monkeypatch, path_exists, mock_files):
    system_paths = [Path('/usr/lib/python3.9/site-packages')]
    rpm_files = {}

    def mock_is_dir(self):
        return path_exists

    monkeypatch.setattr(Path, 'is_dir', mock_is_dir)

    if mock_files is not None:
        def mock_find_python_related(root):
            return iter(mock_files)
        monkeypatch.setattr(scanthirdpartytargetpythonmodules, 'find_python_related', mock_find_python_related)

    rpms_to_check, unowned = scanthirdpartytargetpythonmodules.scan_python_files(system_paths, rpm_files)

    assert len(rpms_to_check) == 0
    assert len(unowned) == 0


@pytest.mark.parametrize('is_signed,expected_rpm_count,expected_file_count', [
    (False, 1, 2),
    (True, 0, 0),
])
def test_identify_unsigned_rpms(monkeypatch, is_signed, expected_rpm_count, expected_file_count):
    rpms_to_check = defaultdict(list)
    package_name = 'test-package'
    rpms_to_check[package_name] = [
        '/path/to/file1.py',
        '/path/to/file2.py',
    ]

    def mock_has_package(model, pkg_name):
        return is_signed

    monkeypatch.setattr(scanthirdpartytargetpythonmodules, 'has_package', mock_has_package)
    monkeypatch.setattr(api, 'current_logger', logger_mocked())

    third_party_rpms, third_party_files = scanthirdpartytargetpythonmodules.identify_unsigned_rpms(rpms_to_check)

    assert len(third_party_rpms) == expected_rpm_count
    assert len(third_party_files) == expected_file_count

    if not is_signed:
        assert package_name in third_party_rpms
        assert '/path/to/file1.py' in third_party_files
        assert '/path/to/file2.py' in third_party_files


def test_identify_unsigned_rpms_empty_input():
    rpms_to_check = defaultdict(list)

    third_party_rpms, third_party_files = scanthirdpartytargetpythonmodules.identify_unsigned_rpms(rpms_to_check)

    assert len(third_party_rpms) == 0
    assert len(third_party_files) == 0
