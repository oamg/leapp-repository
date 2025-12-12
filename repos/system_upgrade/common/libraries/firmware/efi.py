import os
import re

from leapp.exceptions import StopActorExecution
from leapp.libraries.common.firmware import is_efi
from leapp.libraries.common.partitions import get_partition_for_dir, blk_dev_from_partition
from leapp.libraries.stdlib import api, CalledProcessError, run

EFI_MOUNTPOINT = '/boot/efi/'
"""The path to the required mountpoint for ESP."""


def canonical_path_to_efi_format(canonical_path):
    r"""Transform the canonical path to the UEFI format.

    e.g. /boot/efi/EFI/redhat/shimx64.efi -> \EFI\redhat\shimx64.efi
    (just single backslash; so the string needs to be put into apostrophes
    when used for /usr/sbin/efibootmgr cmd)

    The path has to start with /boot/efi otherwise the path is invalid for UEFI.
    """

    # We want to keep the last "/" of the EFI_MOUNTPOINT
    return canonical_path.replace(EFI_MOUNTPOINT[:-1], "").replace("/", "\\")


class EFIBootLoaderEntry:
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

    def __repr__(self):
        return 'EFIBootLoaderEntry({boot_number}, {label}, {active}, {efi_bin_source})'.format(
            boot_number=repr(self.boot_number),
            label=repr(self.label),
            active=repr(self.active),
            efi_bin_source=repr(self.efi_bin_source)
        )

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
        return EFIBootLoaderEntry._efi_path_to_canonical(match.groups('path')[0])


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
        try:
            result = run(['/usr/sbin/efibootmgr', '-v'])
        except CalledProcessError:
            raise StopActorExecution('Unable to get information about UEFI boot entries.')

        bootmgr_output = result['stdout']

        self.current_bootnum = None
        """The boot number (str) of the current boot."""
        self.next_bootnum = None
        """The boot number (str) of the next boot."""
        self.boot_order = tuple()
        """The tuple of the UEFI boot loader entries in the boot order."""
        self.entries = {}
        """The UEFI boot loader entries {'boot_number': EFIBootLoaderEntry}"""

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

            self.entries[match.group('bootnum')] = EFIBootLoaderEntry(
                boot_number=match.group('bootnum'),
                label=match.group('label'),
                active='*' in match.group('active'),
                efi_bin_source=match.group('bin_source'),
            )

        if not self.entries:
            # it's not expected that no entry exists
            raise StopActorExecution('UEFI: Unable to detect any UEFI bootloader entry.')

    @staticmethod
    def _parse_key_value(bootmgr_output, key):
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

    def _parse_boot_order(self, bootmgr_output):
        # e.g.:  BootOrder: 0001,0002,0000,0003
        read_boot_order = self._parse_key_value(bootmgr_output, 'BootOrder')
        self.boot_order = tuple(read_boot_order.split(','))

        if self.boot_order is None:
            raise StopActorExecution('UEFI: Unable to detect current boot order.')

    def _print_loaded_info(self):
        msg = 'Bootloader setup:'
        msg += '\nCurrent boot: %s' % self.current_bootnum
        msg += '\nBoot order: %s\nBoot entries:' % ', '.join(self.boot_order)
        for bootnum, entry in self.entries.items():
            msg += '\n- %s: %s' % (bootnum, entry.label.rstrip())

        api.current_logger().debug(msg)


def get_efi_partition():
    """
    Return the EFI System Partition (ESP).

    Raise StopActorExecution when:
        - UEFI is not detected,
        - ESP is not mounted where expected,
        - the partition can't be obtained from GRUB.
    """

    if not is_efi():
        raise StopActorExecution('Unable to get ESP when BIOS is used.')

    if not os.path.exists(EFI_MOUNTPOINT) or not os.path.ismount(EFI_MOUNTPOINT):
        raise StopActorExecution(
            'The UEFI has been detected but the ESP is not mounted in /boot/efi as required.'
        )

    return get_partition_for_dir(EFI_MOUNTPOINT)


def get_efi_device():
    """Get the block device on which GRUB is installed."""

    return blk_dev_from_partition(get_efi_partition())
