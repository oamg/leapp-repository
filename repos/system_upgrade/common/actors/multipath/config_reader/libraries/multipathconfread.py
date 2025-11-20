import errno
import os

from leapp.libraries.common import multipathutil
from leapp.libraries.common.config.version import get_source_major_version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, MultipathConfFacts8to9, MultipathConfig8to9, MultipathInfo

_regexes = ('vendor', 'product', 'revision', 'product_blacklist', 'devnode',
            'wwid', 'property', 'protocol')


def _parse_config(path):
    contents = multipathutil.read_config(path)
    if contents is None:
        return None
    conf = MultipathConfig8to9(pathname=path)
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
            if data.option == 'enable_foreign':
                conf.enable_foreign_exists = True
            elif data.option == 'allow_usb_devices':
                conf.allow_usb_exists = True
            elif data.option == 'config_dir':
                conf.config_dir = data.value
        if data.option in _regexes and data.value == '*':
            conf.invalid_regexes_exist = True
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


def is_processable():
    res = has_package(DistributionSignedRPM, 'device-mapper-multipath')
    if not res:
        api.current_logger().debug('device-mapper-multipath is not installed.')
    return res


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

    multipath_info = MultipathInfo(
        is_configured=True,
        config_dir=primary_config.config_dir or '/etc/multipath/conf.d'
    )
    api.produce(multipath_info)

    # Handle upgrade-path-specific config actions
    if get_source_major_version() == '8':
        secondary_configs = _parse_config_dir(multipath_info.config_dir)
        all_configs = [primary_config] + secondary_configs

        config_facts_for_8to9 = MultipathConfFacts8to9(configs=all_configs)
        api.produce(config_facts_for_8to9)
