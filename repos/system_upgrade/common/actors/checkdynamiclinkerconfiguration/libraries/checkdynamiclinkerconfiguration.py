from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import DynamicLinkerConfiguration

LD_SO_CONF_DIR = '/etc/ld.so.conf.d'
LD_SO_CONF_MAIN = '/etc/ld.so.conf'
LD_LIBRARY_PATH_VAR = 'LD_LIBRARY_PATH'
LD_PRELOAD_VAR = 'LD_PRELOAD'
FMT_LIST_SEPARATOR_1 = '\n- '
FMT_LIST_SEPARATOR_2 = '\n    - '


def _report_custom_dynamic_linker_configuration(summary):
    reporting.create_report([
        reporting.Title(
            'Detected customized configuration for dynamic linker.'
        ),
        reporting.Summary(summary),
        reporting.Remediation(hint=('Remove or revert the custom dynamic linker configurations and apply the changes '
                                    'using the ldconfig command. In case of possible active software collections we '
                                    'suggest disabling them persistently.')),
        reporting.RelatedResource('file', '/etc/ld.so.conf'),
        reporting.RelatedResource('directory', '/etc/ld.so.conf.d'),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.OS_FACTS]),
    ])


def check_dynamic_linker_configuration():
    configuration = next(api.consume(DynamicLinkerConfiguration), None)
    if not configuration:
        return

    custom_configurations = ''
    if configuration.main_config.modified:
        custom_configurations += (
            '{}The {} file has unexpected contents:{}{}'
            .format(FMT_LIST_SEPARATOR_1, LD_SO_CONF_MAIN,
                    FMT_LIST_SEPARATOR_2, FMT_LIST_SEPARATOR_2.join(configuration.main_config.modified_lines))
        )

    custom_configs = []
    for config in configuration.included_configs:
        if config.modified:
            custom_configs.append(config.path)

    if custom_configs:
        custom_configurations += (
            '{}The following drop in config files were marked as custom:{}{}'
            .format(FMT_LIST_SEPARATOR_1, FMT_LIST_SEPARATOR_2, FMT_LIST_SEPARATOR_2.join(custom_configs))
        )

    if configuration.used_variables:
        custom_configurations += (
            '{}The following variables contain unexpected dynamic linker configuration:{}{}'
            .format(FMT_LIST_SEPARATOR_1, FMT_LIST_SEPARATOR_2,
                    FMT_LIST_SEPARATOR_2.join(configuration.used_variables))
        )

    if custom_configurations:
        summary = (
            'Custom configurations to the dynamic linker could potentially impact '
            'the upgrade in a negative way. The custom configuration includes '
            'modifications to {main_conf}, custom or modified drop in config '
            'files in the {conf_dir} directory and additional entries in the '
            '{ldlib_envar} or {ldpre_envar} variables. These modifications '
            'configure the dynamic linker to use different libraries that might '
            'not be provided by Red Hat products or might not be present during '
            'the whole upgrade process. The following custom configurations '
            'were detected by leapp:{cust_configs}'
            .format(
                main_conf=LD_SO_CONF_MAIN,
                conf_dir=LD_SO_CONF_DIR,
                ldlib_envar=LD_LIBRARY_PATH_VAR,
                ldpre_envar=LD_PRELOAD_VAR,
                cust_configs=custom_configurations
            )
        )
        _report_custom_dynamic_linker_configuration(summary)
