import pytest
from six import text_type

from leapp.models import BrlttyMigrationDecision


@pytest.mark.parametrize('test_input,expected,migrate_bt,migrate_espeak', [
    ('braille-device bth:AB-cd:ef:01:23:45\n', 'braille-device bluetooth:AB-cd:ef:01:23:45', True, False),
    ('braille-device bluez:AB-cd:ef:01:23:45\n', 'braille-device bluetooth:AB-cd:ef:01:23:45', True, False),
    ('speech-driver es\n', 'speech-driver en', False, True),
    ('braille-device bth:AB-cd:ef:01:23:45\nbraille-device bluez:AB-cd:ef:01:23:45\nspeech-driver es\n',
        'braille-device bluetooth:AB-cd:ef:01:23:45\nbraille-device bluetooth:AB-cd:ef:01:23:45\nspeech-driver es',
        True, False),
    ('braille-device bth:AB-cd:ef:01:23:45\nbraille-device bluez:AB-cd:ef:01:23:45\nspeech-driver es\n',
        'braille-device bth:AB-cd:ef:01:23:45\nbraille-device bluez:AB-cd:ef:01:23:45\nspeech-driver en', False, True),
    ('braille-device bth:AB-cd:ef:01:23:45\nbraille-device bluez:AB-cd:ef:01:23:45\nspeech-driver es\n',
        'braille-device bluetooth:AB-cd:ef:01:23:45\nbraille-device bluetooth:AB-cd:ef:01:23:45\nspeech-driver en',
        True, True),
])
def test_actor_migrate(tmpdir, test_input, expected, migrate_bt, migrate_espeak, current_actor_context):
    brltty_conf = text_type(tmpdir.join('brltty.conf'))
    with open(brltty_conf, 'w') as file_out:
        file_out.write(test_input)
    current_actor_context.feed(BrlttyMigrationDecision(migrate_file=brltty_conf, migrate_bt=migrate_bt,
                               migrate_espeak=migrate_espeak))
    current_actor_context.run()
    with open(brltty_conf, 'r') as file_in:
        data = file_in.read().strip()
    assert expected == data
