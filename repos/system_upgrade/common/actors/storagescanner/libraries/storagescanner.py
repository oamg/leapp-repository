import functools
import os
import subprocess

import pyudev

from leapp import reporting
from leapp.libraries.stdlib import api
from leapp.models import (
    FstabEntry,
    LsblkEntry,
    LvdisplayEntry,
    MountEntry,
    PartitionEntry,
    PvsEntry,
    StorageInfo,
    SystemdMountEntry,
    VgsEntry
)


def aslist(f):
    """ Decorator used to convert generator to list """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        return list(f(*args, **kwargs))
    return inner


def _is_file_readable(path):
    """ Verify if file exists and is readable """
    return os.path.isfile(path) and os.access(path, os.R_OK)


def _get_cmd_output(cmd, delim, expected_len):
    """ Verify if command exists and return output """
    if not any(os.access(os.path.join(path, cmd[0]), os.X_OK) for path in os.environ['PATH'].split(os.pathsep)):
        api.current_logger().warning("'%s': command not found" % cmd[0])
        return

    try:
        # FIXME: Will keep call to subprocess until our stdlib supports "env" parameter
        # when there is any fd except 0,1,2 open, lvm closes the fd and prints a warning.
        # In our case /dev/urandom has other fd opened, probably for caching purposes.
        output = subprocess.check_output(cmd, env={'LVM_SUPPRESS_FD_WARNINGS': '1', 'PATH': os.environ['PATH']})

    except subprocess.CalledProcessError as e:
        api.current_logger().debug("Command '%s' return non-zero exit status: %s" % (" ".join(cmd), e.returncode))
        return

    if bytes is not str:
        output = output.decode('utf-8')

    for entry in output.split('\n'):
        entry = entry.strip()
        if not entry:
            continue

        data = entry.split(delim)
        data.extend([''] * (expected_len - len(data)))

        yield data


@aslist
def _get_partitions_info(partitions_path):
    """ Collect storage info from /proc/partitions file """
    if _is_file_readable(partitions_path):
        with open(partitions_path, 'r') as partitions:
            skipped_header = False
            for entry in partitions:
                if entry.startswith('#'):
                    continue

                if not skipped_header:
                    skipped_header = True
                    continue

                entry = entry.strip()
                if not entry:
                    continue

                major, minor, blocks, name = entry.split()
                yield PartitionEntry(
                    major=major,
                    minor=minor,
                    blocks=blocks,
                    name=name)


@aslist
def _get_fstab_info(fstab_path):
    """ Collect storage info from /etc/fstab file """
    if _is_file_readable(fstab_path):
        with open(fstab_path, 'r') as fstab:
            for line, entry in enumerate(fstab, 1):
                if entry.startswith('#'):
                    continue

                entry = entry.strip()
                if not entry:
                    continue

                entries = entry.split()

                if len(entries) == 4:
                    entries.append('0')

                if len(entries) == 5:
                    entries.append('0')

                if len(entries) != 6:
                    if any(value.startswith('#') for value in entries):
                        remediation = (
                            'Comments in the /etc/fstab file must be at the beginning of the line, your file has a'
                            ' comment at the end of the line at line {}, please edit and fix this, for further'
                            ' information read fstab man page (man 5 fstab).'.format(line)
                        )
                    else:
                        remediation = (
                            'The /etc/fstab file must have at least 4 values and at most 6 per line, your file on the'
                            ' line: {} have {} values, please edit and fix this, for further information read'
                            ' fstab man page (man 5 fstab). '.format(line, len(entries))
                        )
                    summary = (
                        'The fstab configuration file seems to be invalid. You need to fix it to be able to proceed'
                        ' with the upgrade process.'
                    )
                    reporting.create_report([
                        reporting.Title('Problems with parsing data in /etc/fstab'),
                        reporting.Summary(summary),
                        reporting.Severity(reporting.Severity.HIGH),
                        reporting.Groups([reporting.Groups.FILESYSTEM]),
                        reporting.Groups([reporting.Groups.INHIBITOR]),
                        reporting.Remediation(hint=remediation),
                        reporting.RelatedResource('file', '/etc/fstab')
                    ])

                    api.current_logger().error(summary)
                    break

                # NOTE: fstab entries are yielded in the same order as in the /etc/fstab
                fs_spec, fs_file, fs_vfstype, fs_mntops, fs_freq, fs_passno = entries
                yield FstabEntry(
                    fs_spec=fs_spec,
                    fs_file=fs_file,
                    fs_vfstype=fs_vfstype,
                    fs_mntops=fs_mntops,
                    fs_freq=fs_freq,
                    fs_passno=fs_passno)


@aslist
def _get_mount_info(path):
    """ Collect storage info """
    with open(path, 'r') as fp:
        for line in [l.strip() for l in fp.readlines()]:
            device, mount, tp, options, _, _ = line.split(' ')
            yield MountEntry(
                name=device,
                mount=mount,
                tp=tp,
                options=options
            )


@aslist
def _get_lsblk_info():
    """ Collect storage info from lsblk command """
    cmd = ['lsblk', '-pbnr', '--output', 'NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINT']
    for entry in _get_cmd_output(cmd, ' ', 7):
        dev_path, maj_min, rm, bsize, ro, tp, mountpoint = entry
        lsblk_cmd = ['lsblk', '-nr', '--output', 'NAME,KNAME,SIZE', dev_path]
        lsblk_info_for_devpath = next(_get_cmd_output(lsblk_cmd, ' ', 3), None)
        if not lsblk_info_for_devpath:
            return

        name, kname, size = lsblk_info_for_devpath
        yield LsblkEntry(
            name=name,
            kname=kname,
            maj_min=maj_min,
            rm=rm,
            size=size,
            bsize=int(bsize),
            ro=ro,
            tp=tp,
            mountpoint=mountpoint)


@aslist
def _get_pvs_info():
    """ Collect storage info from pvs command """
    for entry in _get_cmd_output(['pvs', '--noheadings', '--separator', r':'], ':', 6):
        pv, vg, fmt, attr, psize, pfree = entry
        yield PvsEntry(
            pv=pv,
            vg=vg,
            fmt=fmt,
            attr=attr,
            psize=psize,
            pfree=pfree)


@aslist
def _get_vgs_info():
    """ Collect storage info from vgs command """
    for entry in _get_cmd_output(['vgs', '--noheadings', '--separator', r':'], ':', 7):
        vg, pv, lv, sn, attr, vsize, vfree = entry
        yield VgsEntry(
            vg=vg,
            pv=pv,
            lv=lv,
            sn=sn,
            attr=attr,
            vsize=vsize,
            vfree=vfree)


@aslist
def _get_lvdisplay_info():
    """ Collect storage info from lvdisplay command """
    for entry in _get_cmd_output(['lvdisplay', '-C', '--noheadings', '--separator', r':'], ':', 12):
        lv, vg, attr, lsize, pool, origin, data, meta, move, log, cpy_sync, convert = entry
        yield LvdisplayEntry(
            lv=lv,
            vg=vg,
            attr=attr,
            lsize=lsize,
            pool=pool,
            origin=origin,
            data=data,
            meta=meta,
            move=move,
            log=log,
            cpy_sync=cpy_sync,
            convert=convert)


@aslist
def _get_systemd_mount_info():
    """
    Collect the same storage info as provided by the systemd-mount command.

    The actual implementation no longer relies on calling the systemd-mount, but rather collects the same information
    from udev directly using pyudev. The systemd-mount output parsing has proved not to be unreliable due to
    its tabular format.
    """
    ctx = pyudev.Context()
    # Filter the devices in the same way `systemd-mount --list` does
    for device in ctx.list_devices(subsystem='block', ID_FS_USAGE='filesystem'):
        # Use 'n/a' to provide the same value for unknown output fields same way the systemd-mount does
        yield SystemdMountEntry(
            node=device.device_node,
            path=device.get('ID_PATH', default='n/a'),
            model=device.get('ID_MODEL', default='n/a'),
            wwn=device.get('ID_WWN', default='n/a'),
            fs_type=device.get('ID_FS_TYPE', default='n/a'),
            label=device.get('ID_FS_LABEL', default='n/a'),
            uuid=device.get('ID_FS_UUID', default='n/a')
        )


def get_storage_info():
    """ Collect multiple info about storage and return it """
    return StorageInfo(
        partitions=_get_partitions_info('/proc/partitions'),
        fstab=_get_fstab_info('/etc/fstab'),
        mount=_get_mount_info('/proc/mounts'),
        lsblk=_get_lsblk_info(),
        pvs=_get_pvs_info(),
        vgs=_get_vgs_info(),
        lvdisplay=_get_lvdisplay_info(),
        systemdmount=_get_systemd_mount_info())
