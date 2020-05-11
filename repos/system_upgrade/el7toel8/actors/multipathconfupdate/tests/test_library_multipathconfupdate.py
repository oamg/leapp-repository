import os

from leapp.libraries.actor import multipathconfupdate
from leapp.libraries.common import multipathutil
from leapp.models import MultipathConfig, MultipathConfigOption

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


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
    [os.path.join(CUR_DIR, 'files/before/default_rhel7.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'),
     False, False, False, True, True, True, True, True, True, False, False, True, False, [], ])

all_devs_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/all_devs.conf'), None, None, None, None, None, None, False, False, False,
     True, True, False, False, True, True,
     [('path_checker', 'rdac'), ('detect_checker', 'yes'), ('features', '2 pg_init_retries 50'),
      ('path_selector', 'service-time 0'), ('fast_io_fail_tmo', '5'), ('no_path_retry', 'queue'), ], ])

empty_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/empty.conf'), None, None, None, None, None, None, False, False, False, False,
     False, False, False, False, False, [], ])

default_rhel8_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/default_rhel8.conf'), 'tur', '/etc/multipath/conf.d', True, True, None, False,
     False, False, False, False, False, False, False, False, False, [], ])

all_the_things_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/all_the_things.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'),
     False, False, False, True, True, True, True, True, True, True, True, True, True,
     [('no_path_retry', 'fail'), ('features', '0')], ])

already_updated_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/already_updated.conf'), None, os.path.join(CUR_DIR, 'files/conf.d'), None,
     None, None, None, False, False, False, False, False, False, False, False, False, [], ])

ugly1_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/ugly1.conf'), 'directio', os.path.join(CUR_DIR, 'files/conf.d'), False, False,
     False, True, True, True, True, True, True, True, True, True, True,
     [('dev_loss_tmo', '60'), ('path_selector', 'service-time 0')], ])

# same results as all_devs_conf
ugly2_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/ugly2.conf'), None, None, None, None, None, None, False, False, False, True,
     True, False, False, True, True,
     [('path_checker', 'rdac'), ('detect_checker', 'yes'), ('features', '2 pg_init_retries 50'),
      ('path_selector', 'service-time 0'), ('fast_io_fail_tmo', '5'), ('no_path_retry', 'queue'), ], ])

just_checker_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/just_checker.conf'), 'rdac', '/etc/multipath/conf.d', True, True, None, False,
     False, False, False, False, False, False, False, False, False, [], ])

just_detect_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/just_detect.conf'), None, None, None, False, None, None, False, False, False,
     False, False, False, False, False, False, [], ])

just_reassign_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/just_reassign.conf'), None, None, None, None, None, True, False, False, False,
     False, False, False, False, False, False, [], ])

just_exists_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/just_exists.conf'), None, None, None, None, None, None, False, False, False,
     False, False, False, False, True, False, [], ])

just_all_devs_conf = build_config(
    [os.path.join(CUR_DIR, 'files/before/just_all_devs.conf'), None, None, None, None, None, None, False, False, False,
     False, False, False, False, False, True, [], ])


def test_configs():
    tests = [(default_rhel7_conf, os.path.join(CUR_DIR, 'files/after/default_rhel7.conf'),),
             (all_devs_conf, os.path.join(CUR_DIR, 'files/after/all_devs.conf')), (empty_conf, None),
             (default_rhel8_conf, None),
             (all_the_things_conf, os.path.join(CUR_DIR, 'files/after/all_the_things.conf'),),
             (already_updated_conf, None), (ugly1_conf, os.path.join(CUR_DIR, 'files/after/ugly1.conf')),
             (ugly2_conf, os.path.join(CUR_DIR, 'files/after/ugly2.conf')),
             (just_checker_conf, os.path.join(CUR_DIR, 'files/after/just_checker.conf'),),
             (just_detect_conf, os.path.join(CUR_DIR, 'files/after/just_detect.conf'),),
             (just_reassign_conf, os.path.join(CUR_DIR, 'files/after/just_reassign.conf'),),
             (just_exists_conf, os.path.join(CUR_DIR, 'files/after/just_exists.conf'),),
             (just_all_devs_conf, os.path.join(CUR_DIR, 'files/after/just_all_devs.conf'),), ]
    for config, expected_config in tests:
        config_lines = multipathconfupdate._update_config(config)
        if config_lines is None:
            assert expected_config is None
            continue
        expected_lines = multipathutil.read_config(expected_config)
        assert expected_lines is not None
        assert len(config_lines) == len(expected_lines)
        for config_line, expected_line in zip(config_lines, expected_lines):
            assert config_line == expected_line
