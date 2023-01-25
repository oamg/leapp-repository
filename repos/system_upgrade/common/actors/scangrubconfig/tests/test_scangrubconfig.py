import os

import pytest

from leapp.libraries.actor import scanner
from leapp.libraries.common.config import architecture, version
from leapp.models import GrubConfigError, Report

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_correct_config_error_detection():
    assert not scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.correct'))
    assert not scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.correct_trailing_space'))
    assert not scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.correct_comment'))
    assert not scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.correct_puppet'))


def test_wrong_config_error_detection():
    assert scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.wrong'))
    assert scanner.detect_config_error(os.path.join(CUR_DIR, 'files/error_detection/grub.wrong1'))


def test_all_errors_produced(current_actor_context, monkeypatch):
    # Tell the actor we are not running on s390x
    monkeypatch.setattr(architecture, 'matches_architecture', lambda _: False)
    monkeypatch.setattr(version, 'get_source_version', lambda: '7.9')
    # Set that all checks failed
    monkeypatch.setattr(scanner, 'is_grub_config_missing_final_newline', lambda _: True)
    monkeypatch.setattr(scanner, 'is_grubenv_corrupted', lambda _: True)
    monkeypatch.setattr(scanner, 'detect_config_error', lambda _: True)
    # Run the actor
    current_actor_context.run()
    # Check that exactly 3 messages of different types are produced
    errors = current_actor_context.consume(GrubConfigError)
    assert len(errors) == 3
    for err_type in [GrubConfigError.ERROR_MISSING_NEWLINE, GrubConfigError.ERROR_CORRUPTED_GRUBENV,
                     GrubConfigError.ERROR_GRUB_CMDLINE_LINUX_SYNTAX]:
        distinct_error = next((e for e in errors if e.error_type == err_type), None)
        assert distinct_error
        assert distinct_error.files


@pytest.mark.parametrize(
    ('config_contents', 'error_detected'),
    [
        ('GRUB_DEFAULT=saved\nGRUB_DISABLE_SUBMENU=true\n', False),
        ('GRUB_DEFAULT=saved\nGRUB_DISABLE_SUBMENU=true', True)
    ]
)
def test_is_grub_config_missing_final_newline(monkeypatch, config_contents, error_detected):

    config_path = '/etc/default/grub'

    def mocked_get_config_contents(path):
        assert path == config_path
        return config_contents

    monkeypatch.setattr(scanner, '_get_config_contents', mocked_get_config_contents)
    assert scanner.is_grub_config_missing_final_newline(config_path) == error_detected


def test_correct_config_corrupted_grubenv():
    assert not scanner.is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/corrupted_grubenv/grubenv.correct'))


def test_wrong_config_corrupted_grubenv():
    assert scanner.is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/corrupted_grubenv/grubenv.wrong1'))
    assert scanner.is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/corrupted_grubenv/grubenv.wrong2'))
