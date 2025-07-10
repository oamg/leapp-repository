import os

import pytest

from leapp import reporting
from leapp.libraries.actor import checkunsafepythonpaths
from leapp.libraries.common import testutils
from leapp.libraries.common.config import version
from leapp.libraries.stdlib import api


@pytest.mark.parametrize("source_version, existing_paths, should_report, expected_path", [
    ('8', ['/usr/lib/python3.9'], True, '/usr/lib/python3.9'),
    ('9', ['/usr/lib/python3.12'], True, '/usr/lib/python3.12'),
    ('8', ['/some/other/path'], False, None),
    ('9', ['/some/other/path'], False, None),
])
def test_unsafe_python(monkeypatch, source_version, existing_paths, should_report, expected_path):
    monkeypatch.setattr(version, 'get_source_major_version', lambda: source_version)
    monkeypatch.setattr(os.path, 'isdir', lambda path: path in existing_paths)
    monkeypatch.setattr(reporting, 'create_report', testutils.create_report_mocked())
    monkeypatch.setattr(api, 'current_logger', testutils.logger_mocked())

    checkunsafepythonpaths.process()

    if should_report:
        assert reporting.create_report.called == 1
        fields = reporting.create_report.report_fields
        assert 'Third-party Python modules detected' in fields['title']
        assert expected_path in fields['summary']
        assert reporting.Groups.PYTHON in fields['groups']
        assert reporting.Severity.HIGH == fields['severity']
    else:
        assert reporting.create_report.called == 0
        assert api.current_logger.infomsg == ['No 3rd party Python modules found, skipping...']
