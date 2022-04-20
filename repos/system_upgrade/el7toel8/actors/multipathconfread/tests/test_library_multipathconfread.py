import os

import pytest

from leapp.libraries.actor import multipathconfread
from leapp.models import MultipathConfFacts, MultipathConfig, MultipathConfigOption

# TODO [Artem] We shouldn't chdir in tests
TEST_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(TEST_DIR)
    yield
    os.chdir(previous_cwd)


CUR_DIR = ""


def build_config(val):
    all_devs_options_val = []
    for name_val, value_val in val[16]:
        option = MultipathConfigOption(name=name_val, value=value_val)
        all_devs_options_val.append(option)
    return MultipathConfig(
            pathname=val[0],
            default_path_checker=val[1],
            config_dir=val[2],
            default_retain_hwhandler=val[3],
            default_detect_prio=val[4],
            default_detect_checker=val[5],
            reassign_maps=val[6],
            hw_str_match_exists=val[7],
            ignore_new_boot_devs_exists=val[8],
            new_bindings_in_boot_exists=val[9],
            unpriv_sgio_exists=val[10],
            detect_path_checker_exists=val[11],
            overrides_hwhandler_exists=val[12],
            overrides_pg_timeout_exists=val[13],
            queue_if_no_path_exists=val[14],
            all_devs_section_exists=val[15],
            all_devs_options=all_devs_options_val)


default_rhel7_conf = build_config(
    [os.path.join(CUR_DIR, 'files/default_rhel7.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'), False,
     False, False, True, True, True, True, True, True, False, False, True, False, [], ])

all_devs_conf = build_config(
    [os.path.join(CUR_DIR, 'files/conf.d/all_devs.conf'), None, None, None, None, None, None, False, False, False,
     True, True, False, False, True, True,
     [('path_checker', 'rdac'), ('detect_checker', 'yes'), ('features', '2 pg_init_retries 50'),
      ('path_selector', 'service-time 0'), ('fast_io_fail_tmo', '5'), ('no_path_retry', 'queue'), ], ])

empty_conf = build_config(
    [os.path.join(CUR_DIR, 'files/conf.d/empty.conf'), None, None, None, None, None, None, False, False, False, False,
     False, False, False, False, False, [], ])

default_rhel8_conf = build_config(
    [os.path.join(CUR_DIR, 'files/default_rhel8.conf'), 'tur', '/etc/multipath/conf.d', True, True, None, False, False,
     False, False, False, False, False, False, False, False, [], ])

all_the_things_conf = build_config(
    [os.path.join(CUR_DIR, 'files/all_the_things.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'), False,
     False, False, True, True, True, True, True, True, True, True, True, True,
     [('no_path_retry', 'fail'), ('features', '0')], ])

already_updated_conf = build_config(
    [os.path.join(CUR_DIR, 'files/already_updated.conf'), None, os.path.join(CUR_DIR, 'files/conf.d'), None, None,
     None, None, False, False, False, False, False, False, False, False, False, [], ])

ugly1_conf = build_config(
    [os.path.join(CUR_DIR, 'files/ugly1.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'), False, False, False,
     True, True, True, True, True, True, True, True, True, True,
     [('dev_loss_tmo', '60'), ('path_selector', 'service-time 0')], ])

# same results as all_devs_conf
ugly2_conf = build_config(
    [os.path.join(CUR_DIR, 'files/ugly2.conf'), None, None, None, None, None, None, False, False, False, True, True,
     False, False, True, True,
     [('path_checker', 'rdac'), ('detect_checker', 'yes'), ('features', '2 pg_init_retries 50'),
      ('path_selector', 'service-time 0'), ('fast_io_fail_tmo', '5'), ('no_path_retry', 'queue'), ], ])

just_checker_conf = build_config(
    [os.path.join(CUR_DIR, 'files/just_checker.conf'), 'rdac', '/etc/multipath/conf.d', True, True, None, False, False,
     False, False, False, False, False, False, False, False, [], ])

just_detect_conf = build_config(
    [os.path.join(CUR_DIR, 'files/just_detect.conf'), None, None, None, False, None, None, False, False, False, False,
     False, False, False, False, False, [], ])

just_reassign_conf = build_config(
    [os.path.join(CUR_DIR, 'files/just_reassign.conf'), None, None, None, None, None, True, False, False, False, False,
     False, False, False, False, False, [], ])

just_exists_conf = build_config(
    [os.path.join(CUR_DIR, 'files/just_exists.conf'), None, None, None, None, None, None, False, False, False, False,
     False, False, False, True, False, [], ])

just_all_devs_conf = build_config(
    [os.path.join(CUR_DIR, 'files/just_all_devs.conf'), None, None, None, None, None, None, False, False, False, False,
     False, False, False, False, True, [], ])


def assert_config(config, expected):
    assert config.pathname == expected.pathname
    assert config.default_path_checker == expected.default_path_checker
    assert config.config_dir == expected.config_dir
    assert config.default_retain_hwhandler == expected.default_retain_hwhandler
    assert config.default_detect_prio == expected.default_detect_prio
    assert config.default_detect_checker == expected.default_detect_checker
    assert config.reassign_maps == expected.reassign_maps
    assert config.hw_str_match_exists == expected.hw_str_match_exists
    assert config.ignore_new_boot_devs_exists == expected.ignore_new_boot_devs_exists
    assert config.new_bindings_in_boot_exists == expected.new_bindings_in_boot_exists
    assert config.unpriv_sgio_exists == expected.unpriv_sgio_exists
    assert config.detect_path_checker_exists == expected.detect_path_checker_exists
    assert config.overrides_hwhandler_exists == expected.overrides_hwhandler_exists
    assert config.overrides_pg_timeout_exists == expected.overrides_pg_timeout_exists
    assert config.queue_if_no_path_exists == expected.queue_if_no_path_exists
    assert config.all_devs_section_exists == expected.all_devs_section_exists
    assert len(config.all_devs_options) == len(expected.all_devs_options)
    for i in range(len(config.all_devs_options)):
        conf_opt = config.all_devs_options[i]
        expt_opt = expected.all_devs_options[i]
        assert conf_opt.name == expt_opt.name
        assert conf_opt.value == expt_opt.value


def test_config_dir(adjust_cwd):
    expected_configs = (default_rhel7_conf, all_devs_conf, empty_conf)
    facts = multipathconfread.get_multipath_conf_facts(config_file=os.path.join(CUR_DIR, 'files/default_rhel7.conf'))
    assert facts
    assert len(facts.configs) == 3
    for i in range(len(facts.configs)):
        assert_config(facts.configs[i], expected_configs[i])


def test_already_rhel8(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/default_rhel8.conf'))
    assert config
    assert_config(config, default_rhel8_conf)


def test_all_the_things(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/all_the_things.conf'))
    assert config
    assert_config(config, all_the_things_conf)


def test_already_updated(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/already_updated.conf'))
    assert config
    assert_config(config, already_updated_conf)


def tests_ugly1(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/ugly1.conf'))
    assert config
    assert_config(config, ugly1_conf)


def tests_ugly2(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/ugly2.conf'))
    assert config
    assert_config(config, ugly2_conf)


def tests_just_checker(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/just_checker.conf'))
    assert config
    assert_config(config, just_checker_conf)


def tests_just_detect(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/just_detect.conf'))
    assert config
    assert_config(config, just_detect_conf)


def tests_just_reassign(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/just_reassign.conf'))
    assert config
    assert_config(config, just_reassign_conf)


def tests_just_exists(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/just_exists.conf'))
    assert config
    assert_config(config, just_exists_conf)


def tests_just_all_devs(adjust_cwd):
    config = multipathconfread._parse_config(os.path.join(CUR_DIR, 'files/just_all_devs.conf'))
    assert config
    assert_config(config, just_all_devs_conf)
