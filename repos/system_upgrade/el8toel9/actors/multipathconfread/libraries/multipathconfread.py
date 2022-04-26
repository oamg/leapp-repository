import errno
import os

from leapp.libraries.common import multipathutil
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    InstalledRedHatSignedRPM,
    MultipathConfFacts8to9,
    MultipathConfig8to9,
    TargetUserSpaceUpgradeTasks
)

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
            api.current_logger().debug('Multipath conf directory ' +
                                       '"{}" doesn\'t exist'.format(config_dir))
        else:
            api.current_logger().warning('Failed to read multipath config ' +
                                         'directory ' +
                                         '"{}": {}'.format(config_dir, e))
    return res


def is_processable():
    res = has_package(InstalledRedHatSignedRPM, 'device-mapper-multipath')
    if not res:
        api.current_logger().debug('device-mapper-multipath is not installed.')
    return res


def get_multipath_conf_facts(config_file='/etc/multipath.conf'):
    res_configs = []
    conf = _parse_config(config_file)
    if not conf:
        return None
    res_configs.append(conf)
    if conf.config_dir:
        res_configs.extend(_parse_config_dir(conf.config_dir))
    else:
        res_configs.extend(_parse_config_dir('/etc/multipath/conf.d'))
    return MultipathConfFacts8to9(configs=res_configs)


def produce_copy_to_target_task():
    """
    Produce task to copy files into the target userspace

    The multipath configuration files are needed when the upgrade init ramdisk
    is generated to ensure we are able to boot into the upgrade environment
    and start the upgrade process itself. By this msg it's told that these
    files/dirs will be available when the upgrade init ramdisk is generated.

    See TargetUserSpaceUpgradeTasks and UpgradeInitramfsTasks for more info.
    """
    # TODO(pstodulk): move the function to the multipathconfcheck actor
    # and get rid of the hardcoded stuff.
    # - The current behaviour looks from the user POV same as before this
    # * commit. I am going to keep the proper fix for additional PR as we do
    # * not want to make the current PR even more complex than now and the solution
    # * is not so trivial.
    # - As well, I am missing some information around xDR devices, which are
    # * possibly not handled correctly (maybe missing some executables?..)
    # * Update: practically we do not have enough info about xDR drivers, but
    # * discussed with Ben Marzinski, as the multipath dracut module includes
    # * the xDR utils stuff, we should handle it in the same way.
    # * See xdrgetuid, xdrgetinfo (these two utils are now missing in our initramfs)
    copy_files = []
    for fname in ['/etc/multipath.conf', '/etc/multipath', '/etc/xdrdevices.conf']:
        if os.path.exists(fname):
            copy_files.append(CopyFile(src=fname))

    if copy_files:
        api.produce(TargetUserSpaceUpgradeTasks(copy_files=copy_files))
