import os

from leapp import reporting
from leapp.libraries.common import mpathfiles
from leapp.reporting import create_report

_DEFAULT_CONFIG_DIR = '/etc/multipath/conf.d'
_DEFAULT_BINDINGS_FILE = '/etc/multipath/bindings'
_DEFAULT_WWIDS_FILE = '/etc/multipath/wwids'
_DEFAULT_PRKEYS_FILE = '/etc/multipath/prkeys'


def _default_config_dir_has_conf_files():
    if not os.path.exists(_DEFAULT_CONFIG_DIR):
        return False
    for filename in os.listdir(_DEFAULT_CONFIG_DIR):
        if filename.endswith('.conf'):
            return True
    return False


def _report_config_dir(config_dir):
    create_report([
        reporting.Title(
            'device-mapper-multipath custom config_dir is deprecated'
        ),
        reporting.Summary(
            'The multipath configuration option "config_dir" is set to '
            '"{cfg_dir}". In RHEL-10, this option is deprecated and unused. '
            'The only valid configuration directory is "{def_cfg_dir}". Any '
            'configuration files in "{cfg_dir}" will be moved to '
            '"{def_cfg_dir}".'.format(
                cfg_dir=config_dir, def_cfg_dir=_DEFAULT_CONFIG_DIR)),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _report_config_dir_conflict(config_dir):
    create_report([
        reporting.Title(
            'device-mapper-multipath config_dir conflict'
        ),
        reporting.Summary(
            'The multipath configuration option "config_dir" is set to '
            '"{cfg_dir}". During the upgrade, configuration files from '
            '"{cfg_dir}" will be moved to "{def_cfg_dir}". However, '
            '"{def_cfg_dir}" already contains .conf files. These existing '
            'files would be added to the multipath configuration after the '
            'upgrade. Please remove or relocate the files in "{def_cfg_dir}" '
            'before upgrading.'.format(
                cfg_dir=config_dir, def_cfg_dir=_DEFAULT_CONFIG_DIR)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _report_files(file_list):
    details = ', '.join(
        '{} (currently "{}") will be moved to "{}"'.format(name, current, default)
        for name, current, default in file_list
    )
    create_report([
        reporting.Title(
            'device-mapper-multipath configuration files will be moved'
        ),
        reporting.Summary(
            'The following multipath configuration file locations are '
            'deprecated and unused in RHEL-10. The files will be moved '
            'to their default locations: {}.'.format(details)),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _report_socket_activation():
    create_report([
        reporting.Title(
            'device-mapper-multipath socket activation is disabled by default'
        ),
        reporting.Summary(
            'In RHEL-10, multipathd socket activation is disabled by '
            'default. If you wish to re-enable it, uncomment '
            '"WantedBy=sockets.target" in '
            '/lib/systemd/system/multipathd.socket'),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _report_dm_nvme_multipathing():
    create_report([
        reporting.Title(
            'device-mapper-multipath NVMe multipathing is no longer supported'
        ),
        reporting.Summary(
            'Only Native NVMe multipathing is supported in RHEL-10. Any '
            'multipath NVMe devices will still work, but they will no '
            'longer be managed by dm-multipath.'),
        reporting.Severity(reporting.Severity.INFO),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def _create_paths_str(paths):
    if len(paths) < 2:
        return paths[0]
    return '{} and {}'.format(', '.join(paths[0:-1]), paths[-1])


def _report_getuid(paths):
    paths_str = _create_paths_str(paths)
    create_report([
        reporting.Title(
            'device-mapper-multipath configuration contains getuid_callout'
        ),
        reporting.Summary(
            'The "getuid_callout" option is no longer supported in '
            'RHEL-10. It must be removed from the multipath '
            'configuration before upgrading. The option was found in '
            '{}.'.format(paths_str)),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.RelatedResource('package', 'device-mapper-multipath')
    ])


def check_configs(facts):
    if not facts.configs:
        return

    primary = facts.configs[0]

    # config_dir: only valid in primary config
    config_dir = primary.config_dir
    if (
        config_dir is not None and
        os.path.normpath(config_dir) != _DEFAULT_CONFIG_DIR
    ):
        _report_config_dir(config_dir)
        if _default_config_dir_has_conf_files():
            _report_config_dir_conflict(config_dir)

    bindings_file, wwids_file, prkeys_file = mpathfiles.mpath_file_locations(facts.configs)

    file_list = []
    files_to_report = [
        ('bindings_file', bindings_file, _DEFAULT_BINDINGS_FILE),
        ('wwids_file', wwids_file, _DEFAULT_WWIDS_FILE),
        ('prkeys_file', prkeys_file, _DEFAULT_PRKEYS_FILE),
    ]

    for file_name, configured_path, default_path in files_to_report:
        if (
            configured_path is not None and
            os.path.normpath(configured_path) != default_path
        ):
            file_list.append((file_name, configured_path, default_path))

    if file_list:
        _report_files(file_list)

    # socket activation and dm nvme multipathing: system-level, primary only
    if primary.has_socket_activation:
        _report_socket_activation()
    if primary.has_dm_nvme_multipathing:
        _report_dm_nvme_multipathing()

    # getuid: per-file, report if any config has it
    getuid_paths = [conf.pathname for conf in facts.configs if conf.has_getuid]
    if getuid_paths:
        _report_getuid(getuid_paths)
