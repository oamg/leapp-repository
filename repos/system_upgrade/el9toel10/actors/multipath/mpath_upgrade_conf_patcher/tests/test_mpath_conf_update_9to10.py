import os

import pytest

from leapp.libraries.actor import mpathconfupdate
from leapp.libraries.common import multipathutil
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import MultipathConfFacts9to10, MultipathConfig9to10

BEFORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/before')
AFTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/after')


def build_config(pathname, config_dir=None, bindings_file=None,
                 wwids_file=None, prkeys_file=None):
    return MultipathConfig9to10(
        pathname=pathname,
        config_dir=config_dir,
        bindings_file=bindings_file,
        wwids_file=wwids_file,
        prkeys_file=prkeys_file,
    )


def build_facts(confs):
    return MultipathConfFacts9to10(configs=confs)


def mock_read_config(path):
    return multipathutil.read_config_orig(os.path.join(BEFORE_DIR, path))


# Configs with no changes needed
no_deprecated_conf = build_config('no_deprecated.conf')
empty_conf = build_config('empty.conf')
no_defaults_conf = build_config('no_defaults.conf')

# Configs with deprecated options
has_config_dir_conf = build_config(
    'has_config_dir.conf', config_dir='/etc/multipath/custom.d')
has_files_conf = build_config(
    'has_files.conf', bindings_file='/tmp/bindings',
    wwids_file='/tmp/wwids', prkeys_file='/tmp/prkeys')
all_deprecated_conf = build_config(
    'all_deprecated.conf', config_dir='/etc/multipath/custom.d',
    bindings_file='/tmp/bindings', wwids_file='/tmp/wwids',
    prkeys_file='/tmp/prkeys')

# Secondary configs
secondary_simple_conf = build_config('secondary_simple.conf')
secondary_with_deprecated_conf = build_config(
    'secondary_with_deprecated.conf', bindings_file='/tmp/bindings')


@pytest.mark.parametrize(
    'config_facts',
    [
        build_facts([no_deprecated_conf]),
        build_facts([empty_conf]),
        build_facts([no_defaults_conf]),
        build_facts([has_config_dir_conf]),
        build_facts([has_files_conf]),
        build_facts([all_deprecated_conf]),
        build_facts([has_config_dir_conf, secondary_simple_conf]),
        build_facts([has_config_dir_conf, secondary_with_deprecated_conf]),
        build_facts([no_deprecated_conf, secondary_simple_conf]),
        build_facts([no_deprecated_conf, secondary_with_deprecated_conf]),
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
    monkeypatch.setattr(mpathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    mpathconfupdate.update_configs(config_facts)

    config_updates = {}
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            config_updates[update.target_path] = update.updated_config_location

    primary = config_facts.configs[0]
    non_default_config_dir = (
        primary.config_dir is not None
        and os.path.normpath(primary.config_dir) != '/etc/multipath/conf.d'
    )

    for idx, config in enumerate(config_facts.configs):
        is_secondary = idx > 0

        if is_secondary:
            target_path = os.path.join(
                '/etc/multipath/conf.d', os.path.basename(config.pathname)
            )
        else:
            target_path = config.pathname

        expected_conf_location = os.path.join(AFTER_DIR, config.pathname)

        if target_path not in config_updates:
            # No update for this config - verify no expected after file exists
            # and it's not a secondary that should have been relocated
            assert not os.path.exists(expected_conf_location)
            assert not (is_secondary and non_default_config_dir)
            continue

        updated_config_location = config_updates[target_path]

        if os.path.exists(expected_conf_location):
            # Config was modified - check contents
            assert updated_config_location in config_writes
            actual_contents = config_writes[updated_config_location]

            updated_config_expected_location = os.path.join(
                mpathconfupdate.MODIFICATIONS_STORE_PATH,
                config.pathname.lstrip('/')
            )
            assert updated_config_location == updated_config_expected_location

            expected_contents = multipathutil.read_config_orig(expected_conf_location)
            assert actual_contents == expected_contents
        else:
            # Unmodified secondary relocated - source is original path
            assert updated_config_location == config.pathname


def test_file_relocation(monkeypatch):
    """Check that non-default file locations produce UpdatedMultipathConfig entries."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    monkeypatch.setattr(multipathutil, 'read_config_orig', multipathutil.read_config, raising=False)
    monkeypatch.setattr(multipathutil, 'read_config', mock_read_config)
    monkeypatch.setattr(multipathutil, 'write_config', lambda loc, contents: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    facts = build_facts([has_files_conf])
    mpathconfupdate.update_configs(facts)

    file_updates = {}
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            file_updates[update.target_path] = update.updated_config_location

    assert file_updates['/etc/multipath/bindings'] == '/tmp/bindings'
    assert file_updates['/etc/multipath/wwids'] == '/tmp/wwids'
    assert file_updates['/etc/multipath/prkeys'] == '/tmp/prkeys'


def test_default_file_locations_no_relocation(monkeypatch):
    """Check that default file locations don't produce relocation entries."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    conf = build_config(
        'has_files.conf',
        bindings_file='/etc/multipath/bindings',
        wwids_file='/etc/multipath/wwids',
        prkeys_file='/etc/multipath/prkeys',
    )

    monkeypatch.setattr(multipathutil, 'read_config_orig', multipathutil.read_config, raising=False)
    monkeypatch.setattr(multipathutil, 'read_config', mock_read_config)
    monkeypatch.setattr(multipathutil, 'write_config', lambda loc, contents: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    facts = build_facts([conf])
    mpathconfupdate.update_configs(facts)

    file_targets = set()
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            file_targets.add(update.target_path)

    # Config itself is modified (has deprecated options in before file), but no file relocations
    assert '/etc/multipath/bindings' not in file_targets
    assert '/etc/multipath/wwids' not in file_targets
    assert '/etc/multipath/prkeys' not in file_targets


def test_last_value_wins_for_files(monkeypatch):
    """Check that the last non-None value wins for file locations."""
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    primary = build_config(
        'no_deprecated.conf', bindings_file='/first/bindings')
    secondary = build_config(
        'secondary_simple.conf', bindings_file='/second/bindings')

    monkeypatch.setattr(multipathutil, 'read_config_orig', multipathutil.read_config, raising=False)
    monkeypatch.setattr(multipathutil, 'read_config', mock_read_config)
    monkeypatch.setattr(multipathutil, 'write_config', lambda loc, contents: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    facts = build_facts([primary, secondary])
    mpathconfupdate.update_configs(facts)

    file_updates = {}
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            file_updates[update.target_path] = update.updated_config_location

    # Last value (/second/bindings) should win
    assert file_updates['/etc/multipath/bindings'] == '/second/bindings'


def test_proposed_config_updates_store(monkeypatch):
    """Check whether configs are being stored in the expected path."""
    config = MultipathConfig9to10(
        pathname='/etc/multipath.conf.d/xy.conf',
        config_dir='',
    )

    produce_mock = produce_mocked()
    monkeypatch.setattr(api, 'produce', produce_mock)

    monkeypatch.setattr(multipathutil, 'write_config', lambda loc, contents: None)
    monkeypatch.setattr(mpathconfupdate, '_update_config', lambda *args: 'new config content')
    monkeypatch.setattr(mpathconfupdate, 'prepare_destination_for_file', lambda file_path: None)
    monkeypatch.setattr(mpathconfupdate, 'prepare_place_for_config_modifications', lambda: None)

    mpathconfupdate.update_configs(MultipathConfFacts9to10(configs=[config]))

    expected_updated_config_path = os.path.join(
        mpathconfupdate.MODIFICATIONS_STORE_PATH,
        'etc/multipath.conf.d/xy.conf'
    )
    found = False
    for config_updates_msg in produce_mock.model_instances:
        for update in config_updates_msg.updates:
            if update.updated_config_location == expected_updated_config_path:
                found = True
    assert found
