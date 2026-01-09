import os

from leapp.libraries.common.utils import read_file
from leapp.libraries.stdlib import api
from leapp.models import NVMEDevice, NVMEInfo

NVME_CLASS_DIR = '/sys/class/nvme'
NVME_CONF_DIR = '/etc/nvme'
NVME_CONF_HOSTID = '/etc/nvme/hostid'
NVME_CONF_HOSTNQN = '/etc/nvme/hostnqn'


class NVMEMissingTransport(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def _get_transport_type(device_path):
    tpath = os.path.join(device_path, 'transport')
    if not os.path.exists(tpath):
        raise NVMEMissingTransport(f'The {tpath} file is missing.')

    transport = read_file(tpath).strip()
    if not transport:
        raise NVMEMissingTransport('The transport type is not defined.')

    return transport


def scan_device(device_name):
    device_path = os.path.join(NVME_CLASS_DIR, device_name)
    if not os.path.isdir(device_path):
        api.current_logger().warning(
            'Cannot scan NVMe device: Following path is not dir: {0}'.format(device_path)
        )
        return None

    try:
        transport = _get_transport_type(device_path)
    except NVMEMissingTransport as e:
        # unexpected; seatbelt - skipping tests
        api.current_logger().warning(
            'Skipping {0} NVMe device: Cannot detect transport type: {1}'.format(device_name, e.message)
        )
        return None

    return NVMEDevice(
        sys_class_path=device_path,
        name=device_name,
        transport=transport
    )


def get_hostid(fpath=NVME_CONF_HOSTID):
    if not os.path.exists(fpath):
        api.current_logger().debug('NVMe hostid config file is missing.')
        return None
    return read_file(fpath).strip()


def get_hostnqn(fpath=NVME_CONF_HOSTNQN):
    if not os.path.exists(fpath):
        api.current_logger().debug('NVMe hostnqn config file is missing.')
        return None
    return read_file(fpath).strip()


def process():
    if not os.path.isdir(NVME_CLASS_DIR):
        api.current_logger().debug(
            'NVMe is not active: {0} does not exist.'.format(NVME_CLASS_DIR)
        )
        return

    devices = [scan_device(device_name) for device_name in os.listdir(NVME_CLASS_DIR)]
    # drop possible None values from the list
    devices = [dev for dev in devices if dev is not None]
    if not devices:
        # NOTE(pstodulk): This could be suspicious possibly.
        api.current_logger().warning('No NVMe device detected but NVMe seems active.')
        return

    api.produce(NVMEInfo(
        devices=devices,
        hostnqn=get_hostnqn(),
        hostid=get_hostid(),
    ))
