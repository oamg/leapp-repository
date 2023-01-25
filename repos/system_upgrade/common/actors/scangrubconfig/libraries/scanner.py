import os
import re

from leapp.libraries.common.config import architecture, version
from leapp.models import GrubConfigError


def is_grubenv_corrupted(conf_file):
    # grubenv can be missing
    if not os.path.exists(conf_file):
        return False
    # ignore when /boot/grub2/grubenv is a symlink to its EFI counterpart
    if os.path.islink(conf_file) and os.readlink(conf_file) == '../efi/EFI/redhat/grubenv':
        return False
    with open(conf_file, 'r') as config:
        config_contents = config.read()
    return len(config_contents) != 1024 or config_contents[-1] == '\n'


def _get_config_contents(config_path):
    if os.path.isfile(config_path):
        with open(config_path, 'r') as config:
            return config.read()
    return ''


def is_grub_config_missing_final_newline(conf_file):
    config_contents = _get_config_contents(conf_file)
    return config_contents and config_contents[-1] != '\n'


def detect_config_error(conf_file):
    """
    Check grub configuration for syntax error in GRUB_CMDLINE_LINUX value.

    :return: Function returns True if error was detected, otherwise False.
    """
    with open(conf_file, 'r') as f:
        config = f.read()

    pattern = r'GRUB_CMDLINE_LINUX="[^"]+"(?!(\s*$)|(\s+(GRUB|#)))'
    return re.search(pattern, config) is not None


def scan():
    errors = []
    # Check for corrupted grubenv
    if not architecture.matches_architecture(architecture.ARCH_S390X):
        configs = ['/boot/grub2/grubenv', '/boot/efi/EFI/redhat/grubenv']
        corrupted = []
        for cfg in configs:
            if is_grubenv_corrupted(cfg):
                corrupted.append(cfg)
        if corrupted:
            errors.append(GrubConfigError(error_type=GrubConfigError.ERROR_CORRUPTED_GRUBENV, files=corrupted))

    config = '/etc/default/grub'
    # Check for GRUB_CMDLINE_LINUX syntax errors
    # XXX FIXME(ivasilev) Can we make this check a common one? For now let's limit it to rhel7->rhel8 only
    if version.get_source_major_version() == '7':
        if not architecture.matches_architecture(architecture.ARCH_S390X):
            # For now, skip just s390x, that's only one that is failing now
            # because ZIPL is used there
            if detect_config_error(config):
                errors.append(GrubConfigError(error_detected=True, files=[config],
                                              error_type=GrubConfigError.ERROR_GRUB_CMDLINE_LINUX_SYNTAX))

    # Check for missing newline errors
    if is_grub_config_missing_final_newline(config):
        errors.append(GrubConfigError(error_detected=True, error_type=GrubConfigError.ERROR_MISSING_NEWLINE,
                      files=[config]))

    return errors
