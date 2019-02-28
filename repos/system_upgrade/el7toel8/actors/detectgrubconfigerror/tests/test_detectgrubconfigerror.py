from leapp.libraries.actor.scanner import detect_config_error


def test_correct_config():
    assert not detect_config_error('files/grub.correct')
    assert not detect_config_error('files/grub.correct_trailing_space')


def test_wrong_config():
    assert detect_config_error('files/grub.wrong')
    assert detect_config_error('files/grub.wrong1')
