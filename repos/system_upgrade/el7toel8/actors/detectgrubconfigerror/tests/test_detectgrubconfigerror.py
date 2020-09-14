import os

from leapp.libraries.actor.scanner import detect_config_error

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_correct_config():
    assert not detect_config_error(os.path.join(CUR_DIR, 'files/grub.correct'))
    assert not detect_config_error(os.path.join(CUR_DIR, 'files/grub.correct_trailing_space'))
    assert not detect_config_error(os.path.join(CUR_DIR, 'files/grub.correct_comment'))
    assert not detect_config_error(os.path.join(CUR_DIR, 'files/grub.correct_puppet'))


def test_wrong_config():
    assert detect_config_error(os.path.join(CUR_DIR, 'files/grub.wrong'))
    assert detect_config_error(os.path.join(CUR_DIR, 'files/grub.wrong1'))
