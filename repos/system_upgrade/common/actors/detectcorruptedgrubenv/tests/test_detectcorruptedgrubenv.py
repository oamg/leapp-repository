import os

from leapp.libraries.actor.detectcorruptedgrubenv import is_grubenv_corrupted

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_correct_config():
    assert not is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/grubenv.correct'))


def test_wrong_config():
    assert is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/grubenv.wrong1'))
    assert is_grubenv_corrupted(os.path.join(CUR_DIR, 'files/grubenv.wrong2'))
