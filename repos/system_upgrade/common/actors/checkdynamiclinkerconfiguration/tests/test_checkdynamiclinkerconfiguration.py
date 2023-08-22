import pytest

from leapp import reporting
from leapp.libraries.actor.checkdynamiclinkerconfiguration import (
    check_dynamic_linker_configuration,
    LD_LIBRARY_PATH_VAR,
    LD_PRELOAD_VAR
)
from leapp.libraries.common.testutils import create_report_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import DynamicLinkerConfiguration, LDConfigFile, MainLDConfigFile

INCLUDED_CONFIG_PATHS = ['/etc/ld.so.conf.d/dyninst-x86_64.conf',
                         '/etc/ld.so.conf.d/mariadb-x86_64.conf',
                         '/custom/path/custom1.conf']


@pytest.mark.parametrize(('included_configs_modifications', 'used_variables', 'modified_lines'),
                         [
                            ([False, False, False], [], []),
                            ([True, True, True], [], []),
                            ([False, False, False], [LD_LIBRARY_PATH_VAR], []),
                            ([False, False, False], [], ['modified line 1', 'midified line 2']),
                            ([True, False, True], [LD_LIBRARY_PATH_VAR, LD_PRELOAD_VAR], ['modified line']),
                        ])
def test_check_ld_so_configuration(monkeypatch, included_configs_modifications, used_variables, modified_lines):
    assert len(INCLUDED_CONFIG_PATHS) == len(included_configs_modifications)

    main_config = MainLDConfigFile(path="/etc/ld.so.conf", modified=any(modified_lines), modified_lines=modified_lines)
    included_configs = []
    for path, modified in zip(INCLUDED_CONFIG_PATHS, included_configs_modifications):
        included_configs.append(LDConfigFile(path=path, modified=modified))

    configuration = DynamicLinkerConfiguration(main_config=main_config,
                                               included_configs=included_configs,
                                               used_variables=used_variables)

    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(msgs=[configuration]))
    monkeypatch.setattr(reporting, 'create_report', create_report_mocked())

    check_dynamic_linker_configuration()

    report_expected = any(included_configs_modifications) or modified_lines or used_variables
    if not report_expected:
        assert reporting.create_report.called == 0
        return

    assert reporting.create_report.called == 1
    assert 'configuration for dynamic linker' in reporting.create_report.reports[0]['title']
    summary = reporting.create_report.reports[0]['summary']

    if any(included_configs_modifications):
        assert 'The following drop in config files were marked as custom:' in summary
    for config, modified in zip(INCLUDED_CONFIG_PATHS, included_configs_modifications):
        assert modified == (config in summary)

    if modified_lines:
        assert 'The /etc/ld.so.conf file has unexpected contents' in summary
    for line in modified_lines:
        assert line in summary

    if used_variables:
        assert 'The following variables contain unexpected dynamic linker configuration:' in summary
    for var in used_variables:
        assert '- {}'.format(var) in summary
