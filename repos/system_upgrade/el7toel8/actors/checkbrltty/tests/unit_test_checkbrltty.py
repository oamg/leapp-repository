import pytest
from six import text_type

from leapp.libraries.actor import checkbrltty

BRLTTY_CONF = 'brltty.conf'


@pytest.mark.parametrize('test_input,expected_migrate_bt,expected_migrate_espeak', [
    ('braille-device serial:/dev/ttyS0\n', False, False),
    ('braille-device bth:AB-cd:ef:01:23:45\n', True, False),
    ('braille-device bluez:AB-cd:ef:01:23:45\n', True, False),
    ('speech-driver es\n', False, True),
    ('braille-device bth:AB-cd:ef:01:23:45\nbraille-device bluez:AB-cd:ef:01:23:45\nspeech-driver es\n', True, True),
])
def test_actor_check_migration_bth(tmpdir, monkeypatch, test_input, expected_migrate_bt, expected_migrate_espeak,
                                   current_actor_context):
    test_cfg_file = text_type(tmpdir.join(BRLTTY_CONF))
    with open(test_cfg_file, 'w') as file_out:
        file_out.write(test_input)
    monkeypatch.setattr(checkbrltty, 'BrlttyConf', test_cfg_file)
    (migrate_file, migrate_bt, migrate_espeak,) = checkbrltty.check_for_unsupported_cfg()

    if expected_migrate_bt or expected_migrate_espeak:
        assert test_cfg_file == migrate_file
    assert expected_migrate_bt == migrate_bt
    assert expected_migrate_espeak == migrate_espeak
