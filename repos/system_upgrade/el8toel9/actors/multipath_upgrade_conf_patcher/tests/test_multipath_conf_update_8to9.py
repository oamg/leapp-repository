import os

from leapp.libraries.actor import multipathconfupdate
from leapp.libraries.common import multipathutil
from leapp.models import MultipathConfFacts8to9, MultipathConfig8to9

BEFORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/before')
AFTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files/after')

converted_data = {}


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


def mock_write_config(path, contents):
    converted_data[path] = contents


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

facts_list = [build_facts([default_rhel8_conf]),
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
              build_facts([idempotent_conf])]


def _test_facts(facts):
    multipathconfupdate.update_configs(facts)
    for config in facts.configs:
        expected_data = multipathutil.read_config_orig(os.path.join(AFTER_DIR, config.pathname))
        if config.pathname in converted_data:
            assert converted_data[config.pathname] == expected_data
        else:
            assert expected_data is None


def test_all_facts(monkeypatch):
    monkeypatch.setattr(multipathutil, 'read_config_orig', multipathutil.read_config, raising=False)
    monkeypatch.setattr(multipathutil, 'read_config', mock_read_config)
    monkeypatch.setattr(multipathutil, 'write_config', mock_write_config)
    for facts in facts_list:
        _test_facts(facts)
        converted_data.clear()
