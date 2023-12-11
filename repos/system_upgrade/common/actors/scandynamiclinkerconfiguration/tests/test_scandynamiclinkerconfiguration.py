import glob
import os

import pytest

from leapp import reporting
from leapp.libraries.actor import scandynamiclinkerconfiguration
from leapp.libraries.common.testutils import produce_mocked
from leapp.libraries.stdlib import api, CalledProcessError
from leapp.models import DistributionSignedRPM

INCLUDED_CONFIGS_GLOB_DICT_1 = {'/etc/ld.so.conf.d/*.conf': ['/etc/ld.so.conf.d/dyninst-x86_64.conf',
                                                             '/etc/ld.so.conf.d/mariadb-x86_64.conf',
                                                             '/etc/ld.so.conf.d/bind-export-x86_64.conf']}

INCLUDED_CONFIGS_GLOB_DICT_2 = {'/etc/ld.so.conf.d/*.conf': ['/etc/ld.so.conf.d/dyninst-x86_64.conf',
                                                             '/etc/ld.so.conf.d/mariadb-x86_64.conf',
                                                             '/etc/ld.so.conf.d/bind-export-x86_64.conf',
                                                             '/etc/ld.so.conf.d/custom1.conf',
                                                             '/etc/ld.so.conf.d/custom2.conf']}

INCLUDED_CONFIGS_GLOB_DICT_3 = {'/etc/ld.so.conf.d/*.conf': ['/etc/ld.so.conf.d/dyninst-x86_64.conf',
                                                             '/etc/ld.so.conf.d/custom1.conf',
                                                             '/etc/ld.so.conf.d/mariadb-x86_64.conf',
                                                             '/etc/ld.so.conf.d/bind-export-x86_64.conf',
                                                             '/etc/ld.so.conf.d/custom2.conf'],
                                '/custom/path/*.conf': ['/custom/path/custom1.conf',
                                                        '/custom/path/custom2.conf']}


@pytest.mark.parametrize(('included_configs_glob_dict', 'other_lines', 'custom_configs', 'used_variables'),
                         [
                            (INCLUDED_CONFIGS_GLOB_DICT_1, [], [], []),
                            (INCLUDED_CONFIGS_GLOB_DICT_1, ['/custom/path.lib'], [], []),
                            (INCLUDED_CONFIGS_GLOB_DICT_1, [], [], ['LD_LIBRARY_PATH']),
                            (INCLUDED_CONFIGS_GLOB_DICT_2, [], ['/etc/ld.so.conf.d/custom1.conf',
                                                                '/etc/ld.so.conf.d/custom2.conf'], []),
                            (INCLUDED_CONFIGS_GLOB_DICT_3, ['/custom/path.lib'], ['/etc/ld.so.conf.d/custom1.conf',
                                                                                  '/etc/ld.so.conf.d/custom2.conf'
                                                                                  '/custom/path/custom1.conf',
                                                                                  '/custom/path/custom2.conf'], []),
                        ])
def test_scan_dynamic_linker_configuration(monkeypatch, included_configs_glob_dict, other_lines,
                                           custom_configs, used_variables):
    monkeypatch.setattr(scandynamiclinkerconfiguration, '_parse_main_config',
                        lambda: (included_configs_glob_dict.keys(), other_lines))
    monkeypatch.setattr(glob, 'glob', lambda glob: included_configs_glob_dict[glob])
    monkeypatch.setattr(scandynamiclinkerconfiguration, '_is_included_config_custom',
                        lambda config: config in custom_configs)
    monkeypatch.setattr(api, 'produce', produce_mocked())

    for var in used_variables:
        monkeypatch.setenv(var, '/some/path')

    scandynamiclinkerconfiguration.scan_dynamic_linker_configuration()

    produce_expected = custom_configs or other_lines or used_variables
    if not produce_expected:
        assert not api.produce.called
        return

    assert api.produce.called == 1

    configuration = api.produce.model_instances[0]

    all_configs = []
    for configs in included_configs_glob_dict.values():
        all_configs += configs

    assert len(all_configs) == len(configuration.included_configs)
    for config in configuration.included_configs:
        if config.path in custom_configs:
            assert config.modified

    assert configuration.main_config.path == scandynamiclinkerconfiguration.LD_SO_CONF_MAIN
    if other_lines:
        assert configuration.main_config.modified
        assert configuration.main_config.modified_lines == other_lines

    if used_variables:
        assert configuration.used_variables == used_variables


@pytest.mark.parametrize(('config_contents', 'included_config_paths', 'other_lines'),
                         [
                            (['include ld.so.conf.d/*.conf\n'],
                             ['/etc/ld.so.conf.d/*.conf'], []),
                            (['include ld.so.conf.d/*.conf\n', '\n', '/custom/path.lib\n', '#comment'],
                             ['/etc/ld.so.conf.d/*.conf'], ['/custom/path.lib']),
                            (['include ld.so.conf.d/*.conf\n', 'include /custom/path.conf\n'],
                             ['/etc/ld.so.conf.d/*.conf', '/custom/path.conf'], []),
                            (['include ld.so.conf.d/*.conf\n', '#include /custom/path.conf\n', '#/custom/path.conf\n'],
                             ['/etc/ld.so.conf.d/*.conf'], []),
                            ([' \n'],
                             [], [])
                         ])
def test_parse_main_config(monkeypatch, config_contents, included_config_paths, other_lines):
    def mocked_read_file(path):
        assert path == scandynamiclinkerconfiguration.LD_SO_CONF_MAIN
        return config_contents

    monkeypatch.setattr(scandynamiclinkerconfiguration, '_read_file', mocked_read_file)

    _included_config_paths, _other_lines = scandynamiclinkerconfiguration._parse_main_config()

    assert _included_config_paths == included_config_paths
    assert _other_lines == other_lines


@pytest.mark.parametrize(('config_path', 'run_result', 'is_modified'),
                         [
                            ('/etc/ld.so.conf.d/dyninst-x86_64.conf',
                             '.......T.  c /etc/ld.so.conf.d/dyninst-x86_64.conf', False),
                            ('/etc/ld.so.conf.d/dyninst-x86_64.conf',
                             'S.5....T.  c /etc/ld.so.conf.d/dyninst-x86_64.conf', True),
                            ('/etc/ld.so.conf.d/kernel-3.10.0-1160.el7.x86_64.conf',
                             '', False)
                         ])
def test_is_modified(monkeypatch, config_path, run_result, is_modified):
    def mocked_run(command, checked):
        assert config_path in command
        assert checked is False
        exit_code = 1 if run_result else 0
        return {'stdout': run_result, 'exit_code': exit_code}

    monkeypatch.setattr(scandynamiclinkerconfiguration, 'run', mocked_run)

    _is_modified = scandynamiclinkerconfiguration._is_modified(config_path)
    assert _is_modified == is_modified


@pytest.mark.parametrize(('config_path',
                          'config_contents', 'run_result',
                          'is_installed_rh_signed_package', 'is_modified', 'has_effective_lines'),
                         [
                            ('/etc/ld.so.conf.d/dyninst-x86_64.conf',
                             ['/usr/lib64/dyninst\n'], 'dyninst',
                             True, False, True),  # RH sighend package without modification - Not custom
                            ('/etc/ld.so.conf.d/dyninst-x86_64.conf',
                             ['/usr/lib64/my_dyninst\n'], 'dyninst',
                             True, True, True),  # Was modified by user - Custom
                            ('/etc/custom/custom.conf',
                             ['/usr/lib64/custom'], 'custom',
                             False, None, True),  # Third-party package - Custom
                            ('/etc/custom/custom.conf',
                             ['#/usr/lib64/custom\n'], 'custom',
                             False, None, False),  # Third-party package without effective lines - Not custom
                            ('/etc/ld.so.conf.d/somelib.conf',
                             ['/usr/lib64/somelib\n'], CalledProcessError,
                             None, None, True),  # User created configuration file - Custom
                            ('/etc/ld.so.conf.d/somelib.conf',
                             ['#/usr/lib64/somelib\n'], CalledProcessError,
                             None, None, False)  # User created configuration file without effective lines - Not custom
                         ])
def test_is_included_config_custom(monkeypatch, config_path, config_contents, run_result,
                                   is_installed_rh_signed_package, is_modified, has_effective_lines):
    def mocked_run(command):
        assert config_path in command
        if run_result and not isinstance(run_result, str):
            raise CalledProcessError("message", command, "result")
        return {'stdout': run_result}

    def mocked_has_package(model, package_name):
        assert model is DistributionSignedRPM
        assert package_name == run_result
        return is_installed_rh_signed_package

    def mocked_read_file(path):
        assert path == config_path
        return config_contents

    monkeypatch.setattr(scandynamiclinkerconfiguration, 'run', mocked_run)
    monkeypatch.setattr(scandynamiclinkerconfiguration, 'has_package', mocked_has_package)
    monkeypatch.setattr(scandynamiclinkerconfiguration, '_read_file', mocked_read_file)
    monkeypatch.setattr(scandynamiclinkerconfiguration, '_is_modified', lambda *_: is_modified)
    monkeypatch.setattr(os.path, 'isfile', lambda _: True)

    result = scandynamiclinkerconfiguration._is_included_config_custom(config_path)
    is_custom = not isinstance(run_result, str) or not is_installed_rh_signed_package or is_modified
    is_custom &= has_effective_lines
    assert result == is_custom
