import os
import subprocess
import functools


from leapp.models import StorageInfo, PartitionEntry, FstabEntry, MountEntry, LsblkEntry, \
    PvsEntry, VgsEntry, LvdisplayEntry, SystemdMountEntry
from leapp import reporting
from leapp.libraries.stdlib import api


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
                        reporting.Groups([reporting.Groups.FILESYSTEM, reporting.Groups.INHIBITOR]),
                        reporting.Remediation(hint=remediation),
                        reporting.RelatedResource('file', '/etc/fstab')
                    ])

                    api.current_logger().error(summary)
                    break

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
    for entry in _get_cmd_output(['lsblk', '-r', '--noheadings'], ' ', 7):
        name, maj_min, rm, size, ro, tp, mountpoint = entry
        yield LsblkEntry(
            name=name,
            maj_min=maj_min,
            rm=rm,
            size=size,
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
    """ Collect storage info from systemd-mount command """
    for entry in _get_cmd_output(['systemd-mount', '--list'], ' ', 7):
        # We need to filter the entry because there is a ton of whitespace.
        node, path, model, wwn, fs_type, label, uuid = [x for x in entry if x != '']
        if node == "NODE":
            # First row of the "systemd-mount --list" output is a header.
            # Just skip it.
            continue
        yield SystemdMountEntry(
            node=node,
            path=path,
            model=model,
            wwn=wwn,
            fs_type=fs_type,
            label=label,
            uuid=uuid)


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
