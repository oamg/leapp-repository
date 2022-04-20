import errno
import os

from leapp.libraries.common import multipathutil
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    InstalledRedHatSignedRPM,
    MultipathConfFacts,
    MultipathConfig,
    MultipathConfigOption,
    TargetUserSpaceUpgradeTasks
)


def _change_existing_option(curr_options, opt_name, opt_value):
    for option in curr_options:
        if option.name == opt_name:
            option.value = opt_value  # latest value is used
            return True
    return False


def _add_options(curr_options, new_options):
    ignore = ['hardware_handler', 'pg_timeout', 'product', 'unpriv_sgio',
              'product_blacklist', 'revision', 'vendor']
    for opt_name, opt_value in new_options:
        if opt_name in ignore:
            continue
        if opt_name == 'detect_path_checker':
            opt_name = 'detect_checker'
        if not _change_existing_option(curr_options, opt_name, opt_value):
            curr_options.append(MultipathConfigOption(name=opt_name,
                                                      value=opt_value))


def _remove_qinp(value):
    items = value.split()
    if items == [] or not items[0].isdigit():
        return value
    nr_features = int(items[0])
    if nr_features != len(items) - 1:
        return value
    try:
        items.remove('queue_if_no_path')
    except ValueError:
        return value
    items[0] = str(nr_features - 1)
    return ' '.join(items)


def _fix_qinp_options(options):
    have_npr = False
    need_npr = False
    for option in options:
        if option.name == 'features' and 'queue_if_no_path' in option.value:
            option.value = _remove_qinp(option.value)
            need_npr = True
        if option.name == 'no_path_retry':
            have_npr = True
    if need_npr and not have_npr:
        options.append(MultipathConfigOption(name='no_path_retry',
                                             value='queue'))


def _options_match(overrides, all_devs):
    if overrides == 'detect_path_checker' and all_devs == 'detect_checker':
        return True
    if overrides in ('path_checker', 'checker') and \
            all_devs in ('path_checker', 'checker'):
        return True
    if overrides == all_devs:
        return True
    return False


def _filter_options(all_dev_options, overrides_options):
    for name, value in overrides_options:
        if name == 'features' and 'queue_if_no_path' in value:
            overrides_options.append(('no_path_retry', 'queue'))
            break
    for name, _value in overrides_options:
        for option in all_dev_options:
            if _options_match(name, option.name):
                all_dev_options.remove(option)
                break


def _parse_config(path):
    contents = multipathutil.read_config(path)
    if contents is None:
        return None
    conf = MultipathConfig(pathname=path)
    conf.all_devs_options = []
    section = None
    in_subsection = False
    device_options = []
    overrides_options = []
    in_all_devs = False
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
                if in_all_devs:
                    _add_options(conf.all_devs_options, device_options)
                in_all_devs = False
                device_options = []
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
            if data.option in ('path_checker', 'checker'):
                conf.default_path_checker = data.value
            elif data.option == 'config_dir':
                conf.config_dir = data.value
            elif data.option == 'retain_attached_hw_handler':
                conf.default_retain_hwhandler = data.is_enabled()
            elif data.option == 'detect_prio':
                conf.default_detect_prio = data.is_enabled()
            elif data.option == 'detect_path_checker':
                conf.default_detect_checker = data.is_enabled()
            elif data.option == 'reassign_maps':
                conf.reassign_maps = data.is_enabled()
            elif data.option == 'hw_str_match':
                conf.hw_str_match_exists = True
            elif data.option == 'ignore_new_boot_devs':
                conf.ignore_new_boot_devs_exists = True
            elif data.option == 'new_bindings_in_boot':
                conf.new_bindings_in_boot_exists = True
        if section == 'devices' and in_subsection:
            if data.option == 'all_devs' and data.is_enabled():
                conf.all_devs_section_exists = True
                in_all_devs = True
            else:
                device_options.append((data.option, data.value))
        if section == 'overrides':
            if data.option == 'hardware_handler':
                conf.overrides_hwhandler_exists = True
            elif data.option == 'pg_timeout':
                conf.overrides_pg_timeout_exists = True
            else:
                overrides_options.append((data.option, data.value))
        if data.option == 'unpriv_sgio':
            conf.unpriv_sgio_exists = True
        if data.option == 'detect_path_checker':
            conf.detect_path_checker_exists = True
        if data.option == 'features' and 'queue_if_no_path' in data.value:
            conf.queue_if_no_path_exists = True

    if in_subsection and in_all_devs:
        _add_options(conf.all_devs_options, device_options)
    _fix_qinp_options(conf.all_devs_options)
    _filter_options(conf.all_devs_options, overrides_options)
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
    return MultipathConfFacts(configs=res_configs)


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
