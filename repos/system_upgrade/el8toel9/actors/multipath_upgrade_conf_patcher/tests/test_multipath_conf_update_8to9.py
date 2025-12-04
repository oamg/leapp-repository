import os

import pytest

from leapp.libraries.actor import multipathconfupdate
from leapp.libraries.common import multipathutil
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MultipathConfFacts8to9, MultipathConfig8to9

BEFORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/before')
AFTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/after')


def build_config(pathname, config_dir, enable_foreign_exists, invalid_regexes_exist, allow_usb_exists):
    return MultipathConfig8to9(
        pathname=pathname,
        config_dir=config_dir,
        enable_foreign_exists=enable_foreign_exists,
        invalid_regexes_exist=invalid_regexes_exist,
        allow_usb_exists=allow_usb_exists,
    )


def build_facts(confs):
    return MultipathConfFacts8to9(configs=confs)


def mock_read_config(path):
    """convert to full pathname"""
    return multipathutil.read_config_orig(os.path.join(BEFORE_DIR, path))


default_rhel8_conf = build_config(
    'default_rhel8.conf', None, True, False, False)

all_the_things_conf = build_config(
    'all_the_things.conf', None, False, True, False)

converted_the_things_conf = build_config(
    'converted_the_things.conf', None, True, False, True)

idempotent_conf = build_config(
    'converted_the_things.conf', None, False, True, False)

complicated_conf = build_config(
    'complicated.conf', '/etc/multipath/conf.d', True, True, False)

no_foreign_conf = build_config(
    'no_foreign.conf', None, False, True, True)

allow_usb_conf = build_config(
    'allow_usb.conf', None, False, False, True)

no_defaults_conf = build_config(
    'no_defaults.conf', None, False, True, False)

two_defaults_conf = build_config(
    'two_defaults.conf', None, True, False, False)

empty_conf = build_config(
    'empty.conf', None, False, False, False)

missing_dir_conf = build_config(
    'missing_dir.conf', 'missing', False, True, False)

not_set_dir_conf = build_config(
    'not_set_dir.conf', 'conf1.d', False, True, False)

empty1_conf = build_config(
    'conf1.d/empty.conf', None, False, False, False)

nothing_important_conf = build_config(
    'conf1.d/nothing_important.conf', 'this_gets_ignored', False, False, False)

set_in_dir_conf = build_config(
    'set_in_dir.conf', 'conf2.d', False, False, False)

all_true_conf = build_config(
    'conf2.d/all_true.conf', None, True, True, True)

empty_dir_conf = build_config(
    'empty_dir.conf', 'conf3.d', False, False, False)


@pytest.mark.parametrize(
    'config_facts',
    [
        build_facts([default_rhel8_conf]),
        build_facts([all_the_things_conf]),
        build_facts([converted_the_things_conf]),
        build_facts([complicated_conf]),
        build_facts([no_foreign_conf]),
        build_facts([allow_usb_conf]),
        build_facts([no_defaults_conf]),
        build_facts([two_defaults_conf]),
        build_facts([empty_conf]),
        build_facts([missing_dir_conf]),
        build_facts([empty_dir_conf]),
        build_facts([not_set_dir_conf, empty1_conf, nothing_important_conf]),
        build_facts([set_in_dir_conf, all_true_conf]),
        build_facts([idempotent_conf])
    ]
)
def test_all_facts(monkeypatch, config_facts):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    config_writes = {}

    def write_config_mock(location, contents):
        config_writes[location] = contents

    monkeypatch.setattr(multipathutil, 'read_config_orig', multipathutil.read_config, raising=False)
    monkeypatch.setattr(multipathutil, 'read_config', mock_read_config)
    monkeypatch.setattr(multipathutil, 'write_config', write_config_mock)
    monkeypatch.setattr(multipathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(multipathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    multipathconfupdate.update_configs(config_facts)

    config_updates = {}
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            config_updates[update.target_path] = update.updated_config_location

    for config in config_facts.configs:
        expected_conf_location = os.path.join(AFTER_DIR, config.pathname)

        if config.pathname not in config_updates:
            assert not os.path.exists(expected_conf_location)
            continue

        updated_config_location = config_updates[config.pathname]
        actual_contents = config_writes[updated_config_location]

        updated_config_expected_location = os.path.join(
            multipathconfupdate.MODIFICATIONS_STORE_PATH,
            config.pathname.lstrip('/')
        )

        assert updated_config_location == updated_config_expected_location

        expected_contents = multipathutil.read_config_orig(expected_conf_location)
        assert actual_contents == expected_contents


def test_proposed_config_updates_store(monkeypatch):
    """ Check whether configs are being stored in the expected path. """
    config = MultipathConfig8to9(
        pathname='/etc/multipath.conf.d/xy.conf',
        config_dir='',
        enable_foreign_exists=False,
        invalid_regexes_exist=False,
        allow_usb_exists=False,
    )

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    config_writes = {}

    def write_config_mock(location, contents):
        config_writes[location] = contents

    monkeypatch.setattr(multipathutil, 'write_config', write_config_mock)
    monkeypatch.setattr(multipathconfupdate, '_update_config', lambda *args: 'new config content')
    monkeypatch.setattr(multipathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(multipathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    multipathconfupdate.update_configs(MultipathConfFacts8to9(configs=[config]))

    expected_updated_config_path = os.path.join(
        multipathconfupdate.MODIFICATIONS_STORE_PATH,
        'etc/multipath.conf.d/xy.conf'
    )
    assert expected_updated_config_path in config_writes
