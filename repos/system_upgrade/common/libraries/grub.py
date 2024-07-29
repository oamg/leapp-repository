import os
import re

from leapp.exceptions import StopActorExecution
from leapp.libraries.common import mdraid
from leapp.libraries.stdlib import api, CalledProcessError, run
from leapp.utils.deprecation import deprecated

EFI_MOUNTPOINT = "/boot/efi/"
"""The path to the required mountpoint for ESP."""


class EFIBootLoader:
    """
    Representation of an UEFI boot loader entry.
    """

    def __init__(self, boot_number, label, active, efi_bin_source):
        self.boot_number = boot_number
        """Expected string, e.g. '0001'. """

        self.label = label
        """Label of the UEFI entry. E.g. 'Redhat'"""

        self.active = active
        """True when the UEFI entry is active (asterisk is present next to the boot number)"""

        self.efi_bin_source = efi_bin_source
        """Source of the UEFI binary.

        It could contain various values, e.g.:
            FvVol(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)/FvFile(462caa21-7614-4503-836e-8ab6f4662331)
            HD(1,GPT,28c77f6b-3cd0-4b22-985f-c99903835d79,0x800,0x12c000)/File(\\EFI\\redhat\\shimx64.efi)
            PciRoot(0x0)/Pci(0x2,0x3)/Pci(0x0,0x0)N.....YM....R,Y.
        """

    def __eq__(self, other):
        return all(
            [
                self.boot_number == other.boot_number,
                self.label == other.label,
                self.active == other.active,
                self.efi_bin_source == other.efi_bin_source,
            ]
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def is_referring_to_file(self):
        """Return True when the boot source is a file.

        Some sources could refer e.g. to PXE boot. Return true if the source
        refers to a file ("ends with /File(...path...)")

        Does not matter whether the file exists or not.
        """
        return '/File(\\' in self.efi_bin_source

    @staticmethod
    def _efi_path_to_canonical(efi_path):
        return os.path.join(EFI_MOUNTPOINT, efi_path.replace("\\", "/").lstrip("/"))

    def get_canonical_path(self):
        """Return expected canonical path for the referred UEFI bin or None.

        Return None in case the entry is not referring to any UEFI bin
        (e.g. when it refers to a PXE boot).
        """
        if not self.is_referring_to_file():
            return None
        match = re.search(r'/File\((?P<path>\\.*)\)$', self.efi_bin_source)
        return EFIBootLoader._efi_path_to_canonical(match.groups('path')[0])


class EFIBootInfo:
    """
    Data about the current UEFI boot configuration.

    Raise StopActorExecution when:
        - unable to obtain info about the UEFI configuration.
        - BIOS is detected.
        - ESP is not mounted where expected.
    """

    def __init__(self):
        if not is_efi():
            raise StopActorExecution('Unable to collect data about UEFI on a BIOS system.')
        result = run(['/usr/sbin/efibootmgr', '-v'], checked=False)
        if result['exit_code']:
            raise CalledProcessError('Unable to get information about UEFI boot entries.')

        bootmgr_output = result['stdout']

        self.current_bootnum = None
        """The boot number (str) of the current boot."""
        self.next_bootnum = None
        """The boot number (str) of the next boot."""
        self.boot_order = tuple()
        """The tuple of the UEFI boot loader entries in the boot order."""
        self.entries = {}
        """The UEFI boot loader entries {'boot_number': EFIBootLoader}"""

        self._parse_efi_boot_entries(bootmgr_output)
        self._parse_current_bootnum(bootmgr_output)
        self._parse_next_bootnum(bootmgr_output)
        self._parse_boot_order(bootmgr_output)
        self._print_loaded_info()

    def _parse_efi_boot_entries(self, bootmgr_output):
        """
        Return dict of UEFI boot loader entries: {"<boot_number>": EFIBootLoader}
        """

        self.entries = {}
        regexp_entry = re.compile(
            r"^Boot(?P<bootnum>[a-zA-Z0-9]+)(?P<active>\*?)\s*(?P<label>.*?)\t(?P<bin_source>.*)$"
        )

        for line in bootmgr_output.splitlines():
            match = regexp_entry.match(line)
            if not match:
                continue

            self.entries[match.group('bootnum')] = EFIBootLoader(
                boot_number=match.group('bootnum'),
                label=match.group('label'),
                active='*' in match.group('active'),
                efi_bin_source=match.group('bin_source'),
            )

        if not self.entries:
            # it's not expected that no entry exists
            raise StopActorExecution('UEFI: Unable to detect any UEFI bootloader entry.')

    def _parse_key_value(self, bootmgr_output, key):
        # e.g.: <key>: <value>
        for line in bootmgr_output.splitlines():
            if line.startswith(key + ':'):
                return line.split(':')[1].strip()

        return None

    def _parse_current_bootnum(self, bootmgr_output):
        # e.g.: BootCurrent: 0002
        self.current_bootnum = self._parse_key_value(bootmgr_output, 'BootCurrent')

        if self.current_bootnum is None:
            raise StopActorExecution('UEFI: Unable to detect current boot number.')

    def _parse_next_bootnum(self, bootmgr_output):
        # e.g.: BootNext: 0002
        self.next_bootnum = self._parse_key_value(bootmgr_output, 'BootNext')

        if self.current_bootnum is None:
            raise StopActorExecution('UEFI: Unable to detect next boot number.')

    def _parse_boot_order(self, bootmgr_output):
        # e.g.:  BootOrder: 0001,0002,0000,0003
        for line in bootmgr_output.splitlines():
            if line.startswith('BootOrder:'):
                self.boot_order = tuple(line.split(':')[1].strip().split(','))
                return

        raise StopActorExecution('UEFI: Unable to detect current boot order.')

    def _print_loaded_info(self):
        msg = 'Bootloader setup:'
        msg += '\nCurrent boot: %s' % self.current_bootnum
        msg += '\nBoot order: %s\nBoot entries:' % ', '.join(self.boot_order)
        for bootnum, entry in self.entries.items():
            msg += '\n- %s: %s' % (bootnum, entry.label.rstrip())

        api.current_logger().debug(msg)


def has_grub(blk_dev):
    """
    Check whether GRUB is present on block device
    """
    try:
        blk = os.open(blk_dev, os.O_RDONLY)
        mbr = os.read(blk, 512)
    except OSError:
        api.current_logger().warning(
            'Could not read first sector of {} in order to identify the bootloader'.format(blk_dev)
        )
        raise StopActorExecution()
    os.close(blk)
    test = 'GRUB'
    if not isinstance(mbr, str):
        test = test.encode('utf-8')

    return test in mbr


def blk_dev_from_partition(partition):
    """
    Find parent device of /boot partition
    """
    try:
        result = run(['lsblk', '-spnlo', 'name', partition])
    except CalledProcessError:
        api.current_logger().warning(
            'Could not get parent device of {} partition'.format(partition)
        )
        raise StopActorExecution()
    # lsblk "-s" option prints dependencies in inverse order, so the parent device will always
    # be the last or the only device.
    # Command result example:
    # 'result', {'signal': 0, 'pid': 3872, 'exit_code': 0, 'stderr': u'', 'stdout': u'/dev/vda1\n/dev/vda\n'}
    return result['stdout'].strip().split()[-1]


def _get_partition(directory):
    """
    Get partition name of `directory`.
    """

    try:
        result = run(['grub2-probe', '--target=device', directory])
    except CalledProcessError:
        api.current_logger().warning(
            'Could not get name of underlying {} partition'.format(directory)
        )
        raise StopActorExecution()
    except OSError:
        msg = ('Could not get name of underlying {} partition:'
               ' grub2-probe is missing.'
               ' Possibly called on system that does not use GRUB2?').format(directory)
        api.current_logger().warning(msg)
        raise StopActorExecution()

    partition = result['stdout'].strip()
    api.current_logger().info('{} is on {}'.format(directory, partition))

    return partition


def get_boot_partition():
    """
    Get /boot partition name.
    """

    return _get_partition('/boot')


def is_efi():
    """
    Return True if UEFI is used.

    NOTE(pstodulk): the check doesn't have to be valid for hybrid boot (e.g. AWS, Azure, ..)
    """

    return os.path.exists("/sys/firmware/efi")


def get_efi_partition():
    """
    Return the EFI System Partition (ESP).

    Raise StopActorExecution when:
        - UEFI is not detected,
        - ESP is not mounted where expected,
        - the partition can't be obtained from GRUB.
    """

    if not is_efi():
        raise StopActorExecution("Unable to get ESP when BIOS is used.")

    if not os.path.exists(EFI_MOUNTPOINT) or not os.path.ismount(EFI_MOUNTPOINT):
        raise StopActorExecution(
            "The UEFI has been detected but the ESP is not mounted in /boot/efi as required."
        )

    return _get_partition('/boot/efi/')


def get_blk_device(device):
    """
    Get the block device.

    In case of the block device itself (e.g. /dev/sda), return just the block
    device. In case of a partition, return its block device:
        /dev/sda  -> /dev/sda
        /dev/sda1 -> /dev/sda

    Raise CalledProcessError when unable to get the block device.
    """

    result = run(['lsblk', '-spnlo', 'name', device], checked=False)

    if result['exit_code']:
        raise CalledProcessError('Unable to get a block device for {}'.format(device))

    return result['stdout'].strip().splitlines()[-1].strip()


def get_device_number(device):
    """Get the partition number of a particular device.

    This method will use `blkid` to determinate what is the partition number
    related to a particular device.

    :param device: The device to be analyzed.
    :type device: str
    :return: The device partition number.
    :rtype: int
    """

    result = run(
        ['/usr/sbin/blkid', '-p', '-s', 'PART_ENTRY_NUMBER', device],
        checked=False
    )
    output = result['stdout'].strip()

    if result['exit_code']:
        raise CalledProcessError('Unable to get information about the {} device'.format(device))

    if not output:
        raise StopActorExecution('The {} device has no PART_ENTRY_NUMBER'.format(device))

    partition_number = output.split('PART_ENTRY_NUMBER=')[-1].replace('"', '')

    return int(partition_number)


def get_grub_devices():
    """
    Get block devices where GRUB is located. We assume GRUB is on the same device
    as /boot partition is. In case that device is an md (Multiple Device) device, all
    of the component devices of such a device are considered.

    :return: Devices where GRUB is located
    :rtype: list
    """
    boot_device = get_boot_partition()
    devices = []
    if mdraid.is_mdraid_dev(boot_device):
        component_devs = mdraid.get_component_devices(boot_device)
        blk_devs = [blk_dev_from_partition(dev) for dev in component_devs]
        # remove duplicates as there might be raid on partitions on the same drive
        # even if that's very unusual
        devices = sorted(list(set(blk_devs)))
    else:
        devices.append(blk_dev_from_partition(boot_device))

    have_grub = [dev for dev in devices if has_grub(dev)]
    api.current_logger().info('GRUB is installed on {}'.format(",".join(have_grub)))
    return have_grub


@deprecated(since='2023-06-23', message='This function has been replaced by get_grub_devices')
def get_grub_device():
    """
    Get block device where GRUB is located. We assume GRUB is on the same device
    as /boot partition is.

    """
    boot_partition = get_boot_partition()
    grub_dev = blk_dev_from_partition(boot_partition)
    api.current_logger().info('GRUB is installed on {}'.format(grub_dev))
    # if has_grub(grub_dev):
    return grub_dev if has_grub(grub_dev) else None


def is_blscfg_enabled_in_defaultgrub(default_grub_msg):
    """
    Check if GRUB_ENABLE_BLSCFG is true in /etc/default/grub file
    """
    grub_options_lst = default_grub_msg.default_grub_info
    default_grub_options = {
        option.name: option.value.strip('"') for option in grub_options_lst
    }
    return bool(default_grub_options.get('GRUB_ENABLE_BLSCFG', '') == 'true')
