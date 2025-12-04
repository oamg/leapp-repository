import os

from leapp.libraries.common.config import version
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, LVMConfig, LVMConfigDevicesSection

LVM_CONFIG_PATH = '/etc/lvm/lvm.conf'


def _lvm_config_devices_parser(lvm_config_lines):
    in_section = False
    config = {}
    for line in lvm_config_lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if "devices {" in line:
            in_section = True
            continue
        if in_section and "}" in line:
            in_section = False
        if in_section:
            value = line.split("=", 1)
            config[value[0].strip()] = value[1].strip().strip('"')
    return config


def _read_config_lines(path):
    with open(path) as lvm_conf_file:
        return lvm_conf_file.readlines()


def scan():
    if not has_package(DistributionSignedRPM, 'lvm2'):
        return

    if not os.path.isfile(LVM_CONFIG_PATH):
        api.current_logger().debug('The "{}" is not present on the system.'.format(LVM_CONFIG_PATH))
        return

    lvm_config_lines = _read_config_lines(LVM_CONFIG_PATH)
    devices_section = _lvm_config_devices_parser(lvm_config_lines)

    lvm_config_devices = LVMConfigDevicesSection(use_devicesfile=int(version.get_source_major_version()) > 8)
    if 'devicesfile' in devices_section:
        lvm_config_devices.devicesfile = devices_section['devicesfile']

    if 'use_devicesfile' in devices_section and devices_section['use_devicesfile'] in ['0', '1']:
        lvm_config_devices.use_devicesfile = devices_section['use_devicesfile'] == '1'

    api.produce(LVMConfig(devices=lvm_config_devices))
