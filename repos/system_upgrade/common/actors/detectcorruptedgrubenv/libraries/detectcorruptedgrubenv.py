import os


def is_grubenv_corrupted(conf_file):
    # grubenv can be missing
    if not os.path.exists(conf_file):
        return False
    # ignore when /boot/grub2/grubenv is a symlink to its EFI counterpart
    if os.path.islink(conf_file) \
            and os.readlink(conf_file) == '../efi/EFI/redhat/grubenv':
        return False
    with open(conf_file, 'r') as config:
        config_contents = config.read()
    return len(config_contents) != 1024 or config_contents[-1] == '\n'
