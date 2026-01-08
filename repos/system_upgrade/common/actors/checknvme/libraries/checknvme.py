from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import (
    CopyFile,
    DracutModule,
    KernelCmdlineArg,
    NVMEInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
    UpgradeKernelCmdlineArgTasks
)
from leapp.reporting import create_report

FMT_LIST_SEPARATOR = '\n    - '
BROKEN_TRANSPORT_TYPES = ['tcp', 'rdma']
SAFE_TRANSPORT_TYPES = ['pcie', 'fc']
RQ_RPMS_CONTAINER = [
    'iproute',
    'jq',
    'nvme-cli',
    'sed',
]
RQ_CONFIG_FILES = [
    '/etc/nvme/hostid',
    '/etc/nvme/hostnqn',
]
"""
These config files seems to be required, but potentially they could be missing
on the source system. Tracking them explicitly.
"""


def _format_list(data, sep=FMT_LIST_SEPARATOR, callback_sort=sorted, limit=0):
    # NOTE(pstodulk): Teaser O:-> https://issues.redhat.com/browse/RHEL-126447
    if callback_sort is None:
        callback_sort = lambda x: x
    res = ['{}{}'.format(sep, item) for item in callback_sort(data)]
    if limit:
        return ''.join(res[:limit])
    return ''.join(res)


def _register_upgrade_tasks(nvme_fc_devices=None):
    """
    Register tasks that should happen during IPU to handle NVMe devices
    successfully.

    Args:
        nvme_fc_devices (list): List of NVMe-FC devices
    """
    api.produce(TargetUserSpaceUpgradeTasks(
        copy_files=[CopyFile(src='/etc/nvme/')],
        install_rpms=RQ_RPMS_CONTAINER)
    )

    api.produce(UpgradeInitramfsTasks(
        # TODO(pstodulk): the module should take all files as it needs them.
        # Drop the comment when verified, uncomment the line below otherwise
        # include_files=RQ_CONFIG_FILES,
        include_dracut_modules=[DracutModule(name='nvmf')])
    )

    # Add kernel command line argument for NVMe-FC auto-discovery
    if nvme_fc_devices:
        cmdline_args = [KernelCmdlineArg(key='rd.nvmf.discover', value='fc,auto')]
        api.produce(UpgradeKernelCmdlineArgTasks(to_add=cmdline_args))


def report_missing_configs(nvmeinfo, nvmeof_devices):
    # TODO(pstodulk)
    pass


def check_nvme(nvmeinfo):
    """
    Check the system can be configured with discovered NVMe configuration.

    In case the discovered configuration is considered

    Return tuple (upgrade_can_continue, nvme_fc_devices) where:
    - upgrade_can_continue: True if upgrade can continue, False otherwise
    - nvme_fc_devices: List of NVMe-FC devices
    """
    upgrade_can_continue = True
    unhandled_devices = []
    safe_devices = []
    nvmeof_devices = []
    nvme_fc_devices = []

    for device in nvmeinfo.devices:
        if device.transport in BROKEN_TRANSPORT_TYPES:
            unhandled_devices.append(device)
        elif device.transport in SAFE_TRANSPORT_TYPES:
            safe_devices.append(device)
        else:
            # TODO(pstodulk): hm? loop, apple-..., etc. types
            pass
        if device.transport != 'pcie':
            nvmeof_devices.append(device)
        if device.transport == 'fc':
            nvme_fc_devices.append(device)

    if unhandled_devices:
        # TODO(pstodulk): what we will do here? It's not clear whether to stop
        # the upgrade or not, as it could be about devices used for a data
        # storage - unrelated to the system partitions / filesystems.
        # maybe just report potential risk?
        pass

    if nvmeof_devices and not (nvmeinfo.hostid and nvmeinfo.hostnqn):
        # NOTE(pstodulk): hostid and hostnqn are mandatory for NVMe-oF devices.
        # That means practically FC, RDMA, TCP. Let's inform user the upgrade
        # is blocked and they must configure the system properly to be able to
        # upgrade
        upgrade_can_continue = False
        report_missing_configs(nvmeinfo, nvmeof_devices)

    if nvme_fc_devices:
        api.current_logger().info(
            'Detected %d NVMe-FC device(s). Will add rd.nvmf.discover=fc,auto to the upgrade boot entry.',
            len(nvme_fc_devices)
        )

    return upgrade_can_continue, nvme_fc_devices


def process():
    nvmeinfo = next(api.consume(NVMEInfo), None)
    if not nvmeinfo or not nvmeinfo.devices:
        # Nothing to do
        return

    upgrade_can_continue, nvme_fc_devices = check_nvme(nvmeinfo)
    if upgrade_can_continue:
        _register_upgrade_tasks(nvme_fc_devices)

