import os

from leapp.libraries.actor import multipathconfread
from leapp.models import MultipathConfig8to9

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')


def build_config(pathname, config_dir, enable_foreign_exists, invalid_regexes_exist, allow_usb_exists):
    return MultipathConfig8to9(
        pathname=pathname,
        config_dir=config_dir,
        enable_foreign_exists=enable_foreign_exists,
        invalid_regexes_exist=invalid_regexes_exist,
        allow_usb_exists=allow_usb_exists,
    )


def assert_config(config, expected):
    assert config.pathname == expected.pathname
    assert config.config_dir == expected.config_dir
    assert config.enable_foreign_exists == expected.enable_foreign_exists
    assert config.invalid_regexes_exist == expected.invalid_regexes_exist
    assert config.allow_usb_exists == expected.allow_usb_exists


default_rhel8_conf = build_config(
    os.path.join(TEST_DIR, 'default_rhel8.conf'), None, True, False, False)

all_the_things_conf = build_config(
    os.path.join(TEST_DIR, 'all_the_things.conf'), None, False, True, False)

converted_the_things_conf = build_config(
    os.path.join(TEST_DIR, 'converted_the_things.conf'), None, True, False, True)

complicated_conf = build_config(
    os.path.join(TEST_DIR, 'complicated.conf'), "/etc/multipath/conf.d", True, True, False)

no_foreign_conf = build_config(
    os.path.join(TEST_DIR, 'no_foreign.conf'), None, False, True, True)

allow_usb_conf = build_config(
    os.path.join(TEST_DIR, 'allow_usb.conf'), None, False, False, True)

empty_conf = build_config(
    os.path.join(TEST_DIR, 'empty.conf'), None, False, False, False)

missing_dir_conf = build_config(
    os.path.join(TEST_DIR, 'missing_dir.conf'), os.path.join(TEST_DIR, 'missing'), False, True, False)

empty_dir_conf = build_config(
    os.path.join(TEST_DIR, 'empty_dir.conf'), os.path.join(TEST_DIR, 'conf3.d'), False, False, False)

not_set_dir_conf = build_config(
    os.path.join(TEST_DIR, 'not_set_dir.conf'), os.path.join(TEST_DIR, "conf1.d"), False, True, False)

empty1_conf = build_config(
    os.path.join(TEST_DIR, 'conf1.d/empty.conf'), None, False, False, False)

nothing_important_conf = build_config(
    os.path.join(TEST_DIR, 'conf1.d/nothing_important.conf'),
    os.path.join(TEST_DIR, 'this_gets_ignored'), False, False, False)

set_in_dir_conf = build_config(
    os.path.join(TEST_DIR, 'set_in_dir.conf'), os.path.join(TEST_DIR, "conf2.d"), False, False, False)

all_true_conf = build_config(
    os.path.join(TEST_DIR, 'conf2.d/all_true.conf'), None, True, True, True)

no_defaults_conf = build_config(
    os.path.join(TEST_DIR, 'no_defaults.conf'), None, False, True, False)

two_defaults_conf = build_config(
    os.path.join(TEST_DIR, 'two_defaults.conf'), None, True, False, False)


def mock_parse_config(path):
    """Convert config_dir into full pathname"""
    conf = multipathconfread._parse_config_orig(path)
    if not conf:
        return None
    if conf.config_dir:
        conf.config_dir = os.path.join(TEST_DIR, conf.config_dir)
    return conf


def test_parse_config():
    test_map = {'default_rhel8.conf': default_rhel8_conf,
                'all_the_things.conf': all_the_things_conf,
                'converted_the_things.conf': converted_the_things_conf,
                'complicated.conf': complicated_conf,
                'no_foreign.conf': no_foreign_conf,
                'allow_usb.conf': allow_usb_conf,
                'no_defaults.conf': no_defaults_conf,
                'two_defaults.conf': two_defaults_conf,
                'empty.conf': empty_conf}
    for config_name, expected_data in test_map.items():
        config = multipathconfread._parse_config(os.path.join(TEST_DIR, config_name))
        assert config
        assert_config(config, expected_data)


def test_get_facts_missing_dir(monkeypatch):
    monkeypatch.setattr(multipathconfread, '_parse_config_orig', multipathconfread._parse_config, raising=False)
    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse_config)

    facts = multipathconfread.get_multipath_conf_facts(os.path.join(TEST_DIR, 'missing_dir.conf'))
    assert facts
    assert len(facts.configs) == 1
    assert_config(facts.configs[0], missing_dir_conf)


def test_get_facts_empty_dir(monkeypatch):
    monkeypatch.setattr(multipathconfread, '_parse_config_orig', multipathconfread._parse_config, raising=False)
    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse_config)

    facts = multipathconfread.get_multipath_conf_facts(os.path.join(TEST_DIR, 'empty_dir.conf'))
    assert facts
    assert len(facts.configs) == 1
    assert_config(facts.configs[0], empty_dir_conf)


def test_get_facts_not_set_dir(monkeypatch):
    monkeypatch.setattr(multipathconfread, '_parse_config_orig', multipathconfread._parse_config, raising=False)
    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse_config)

    expected_configs = (not_set_dir_conf, empty1_conf, nothing_important_conf)
    facts = multipathconfread.get_multipath_conf_facts(os.path.join(TEST_DIR, 'not_set_dir.conf'))
    assert facts
    assert len(facts.configs) == 3
    for i in range(len(facts.configs)):
        assert_config(facts.configs[i], expected_configs[i])


def test_get_facts_set_in_dir(monkeypatch):
    monkeypatch.setattr(multipathconfread, '_parse_config_orig', multipathconfread._parse_config, raising=False)
    monkeypatch.setattr(multipathconfread, '_parse_config', mock_parse_config)

    expected_configs = (set_in_dir_conf, all_true_conf)
    facts = multipathconfread.get_multipath_conf_facts(os.path.join(TEST_DIR, 'set_in_dir.conf'))
    assert facts
    assert len(facts.configs) == 2
    for i in range(len(facts.configs)):
        assert_config(facts.configs[i], expected_configs[i])
