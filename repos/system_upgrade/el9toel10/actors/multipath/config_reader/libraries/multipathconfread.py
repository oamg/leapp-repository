import errno
import os

from leapp.libraries.common import multipathutil
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, MultipathConfFacts9to10, MultipathConfig9to10, MultipathInfo

_DEFAULT_BINDINGS_FILE = '/etc/multipath/bindings'
_DEFAULT_WWIDS_FILE = '/etc/multipath/wwids'
_DEFAULT_PRKEYS_FILE = '/etc/multipath/prkeys'


def _parse_config(path):
    contents = multipathutil.read_config(path)
    if contents is None:
        return None
    conf = MultipathConfig9to10(pathname=path)
    section = None
    in_subsection = False
    for line in contents.split('\n'):
        try:
            data = multipathutil.LineData(line, section, in_subsection)
        except ValueError:
            continue
        if data.type == data.TYPE_BLANK:
            continue
        if data.type == data.TYPE_SECTION_END:
            if in_subsection:
                in_subsection = False
            elif section:
                section = None
            continue
        if data.type == data.TYPE_SECTION_START:
            if not section:
                section = data.section
            elif not in_subsection:
                in_subsection = True
            continue
        if data.type != data.TYPE_OPTION:
            continue
        if section == 'defaults':
            if data.option == 'config_dir':
                conf.config_dir = data.value
            elif data.option == 'bindings_file':
                conf.bindings_file = data.value
            elif data.option == 'wwids_file':
                conf.wwids_file = data.value
            elif data.option == 'prkeys_file':
                conf.prkeys_file = data.value
        if data.option == 'getuid_callout':
            conf.has_getuid = True
    return conf


def _parse_config_dir(config_dir):
    res = []
    try:
        for config_file in sorted(os.listdir(config_dir)):
            path = os.path.join(config_dir, config_file)
            if not path.endswith('.conf'):
                continue
            conf = _parse_config(path)
            if conf:
                res.append(conf)
    except OSError as e:
        if e.errno == errno.ENOENT:
            api.current_logger().debug(
                'Multipath conf directory "%s" doesn\'t exist',
                config_dir
            )
        else:
            api.current_logger().warning(
                'Failed to read multipath config directory "%s": %s',
                config_dir,
                e
            )
    return res


def _check_socket_activation():
    return os.path.exists(
        '/etc/systemd/system/sockets.target.wants/multipathd.socket'
    )


def _check_dm_nvme_multipathing():
    if not os.path.isdir('/sys/module/nvme_core'):
        return False
    try:
        with open('/sys/module/nvme_core/parameters/multipath', 'r') as f:
            content = f.read().strip()
    except IOError:
        return False
    return content == 'N'


def is_processable():
    res = has_package(DistributionSignedRPM, 'device-mapper-multipath')
    if not res:
        api.current_logger().debug('device-mapper-multipath is not installed.')
    return res


def _add_file_locations(configs, mpath_info):
    bindings_file = None
    wwids_file = None
    prkeys_file = None
    for conf in configs:
        if conf.bindings_file is not None:
            bindings_file = conf.bindings_file
        if conf.wwids_file is not None:
            wwids_file = conf.wwids_file
        if conf.prkeys_file is not None:
            prkeys_file = conf.prkeys_file

    if (
        bindings_file is None or
        os.path.normpath(bindings_file) == _DEFAULT_BINDINGS_FILE
    ):
        mpath_info.bindings_file = _DEFAULT_BINDINGS_FILE
    if (
        wwids_file is None or
        os.path.normpath(wwids_file) == _DEFAULT_WWIDS_FILE
    ):
        mpath_info.wwids_file = _DEFAULT_WWIDS_FILE
    if (
        prkeys_file is None or
        os.path.normpath(prkeys_file) == _DEFAULT_PRKEYS_FILE
    ):
        mpath_info.prkeys_file = _DEFAULT_PRKEYS_FILE


def scan_and_emit_multipath_info(default_config_path='/etc/multipath.conf'):
    if not is_processable():
        return

    primary_config = _parse_config(default_config_path)
    if not primary_config:
        api.current_logger().debug(
            'Primary multipath config /etc/multipath.conf is not present - multipath '
            'is not used.'
        )
        mpath_info = MultipathInfo(is_configured=False)
        api.produce(mpath_info)
        return

    multipath_info = MultipathInfo(is_configured=True)
    # Do not set multipath_info.config_dir to a non-default directory,
    # otherwise any files that exist there will be copied to that directory
    # during the upgrade. Also don't set it to the default directory if you
    # aren't reading config files from there. The directory may exist and have
    # config files which are not used in the existing config, and should not
    # be copied.
    if (
        not primary_config.config_dir or
        os.path.normpath(primary_config.config_dir) == '/etc/multipath/conf.d'
    ):
        multipath_info.config_dir = '/etc/multipath/conf.d'

    primary_config.has_socket_activation = _check_socket_activation()
    primary_config.has_dm_nvme_multipathing = _check_dm_nvme_multipathing()

    secondary_configs = _parse_config_dir(
        primary_config.config_dir or '/etc/multipath/conf.d'
    )
    all_configs = [primary_config] + secondary_configs
    _add_file_locations(all_configs, multipath_info)
    api.produce(multipath_info)

    config_facts_for_9to10 = MultipathConfFacts9to10(configs=all_configs)
    api.produce(config_facts_for_9to10)
