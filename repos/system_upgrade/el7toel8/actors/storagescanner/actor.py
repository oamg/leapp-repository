import os
import subprocess

from leapp.actors import Actor
from leapp.models import StorageInfo, PartitionEntry, FstabEntry, MountEntry, LsblkEntry, PvsEntry, VgsEntry, LvdisplayEntry, SystemdMountEntry
from leapp.tags import IPUWorkflowTag, FactsPhaseTag


class StorageScanner(Actor):
    """
    Provides data about storage settings.

    After collecting data from tools like mount, lsblk, pvs, vgs and lvdisplay, and relevant files
    under /proc/partitions and /etc/fstab, a message with relevant data will be produced.
    """

    name = 'storage_scanner'
    consumes = ()
    produces = (StorageInfo, PartitionEntry,)
    tags = (IPUWorkflowTag, FactsPhaseTag,)


    def is_file_readable(self, path):
        return os.path.isfile(path) and os.access(path, os.R_OK)


    def get_cmd_output(self, cmd, delim, expected_len):
        if not any(os.access(os.path.join(path, cmd[0]), os.X_OK) for path in os.environ['PATH'].split(os.pathsep)):
            self.log.warning("'%s': command not found" % cmd[0])
            raise StopIteration()

        try:
            output = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            self.log.warning("Command '%s' return non-zero exit status: %s" % (" ".join(cmd), e.returncode))
            raise StopIteration()

        for entry in output.split('\n'):
            entry = entry.strip()
            if not entry:
                continue

            data = entry.split(delim)
            data.extend([''] * (expected_len - len(data)))

            yield data


    def process(self):
        result = StorageInfo()

        partitions_path = '/proc/partitions'
        if self.is_file_readable(partitions_path):
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
                    result.partitions.append(PartitionEntry(
                        major=major,
                        minor=minor,
                        blocks=blocks,
                        name=name))

        fstab_path = '/etc/fstab'
        if self.is_file_readable(fstab_path):
            with open(fstab_path, 'r') as fstab:
                for entry in fstab:
                    if entry.startswith('#'):
                        continue

                    entry = entry.strip()
                    if not entry:
                        continue

                    fs_spec, fs_file, fs_vfstype, fs_mntops, fs_freq, fs_passno = entry.split()
                    result.fstab.append(FstabEntry(
                        fs_spec=fs_spec,
                        fs_file=fs_file,
                        fs_vfstype=fs_vfstype,
                        fs_mntops=fs_mntops,
                        fs_freq=fs_freq,
                        fs_passno=fs_passno))

        for entry in self.get_cmd_output(['mount'], ' ', 6):
            name, _, mount, _, tp, options = entry
            result.mount.append(MountEntry(
                name=name,
                mount=mount,
                tp=tp,
                options=options))

        for entry in self.get_cmd_output(['lsblk', '-r', '--noheadings'], ' ', 7):
            name, maj_min, rm, size, ro, tp, mountpoint = entry
            result.lsblk.append(LsblkEntry(
                name=name,
                maj_min=maj_min,
                rm=rm,
                size=size,
                ro=ro,
                tp=tp,
                mountpoint=mountpoint))

        for entry in self.get_cmd_output(['pvs', '--noheadings', '--separator', r':'], ':', 6):
            pv, vg, fmt, attr, psize, pfree = entry
            result.pvs.append(PvsEntry(
                pv=pv,
                vg=vg,
                fmt=fmt,
                attr=attr,
                psize=psize,
                pfree=pfree))

        for entry in self.get_cmd_output(['vgs', '--noheadings', '--separator', r':'], ':', 7):
            vg, pv, lv, sn, attr, vsize, vfree = entry
            result.vgs.append(VgsEntry(
                vg=vg,
                pv=pv,
                lv=lv,
                sn=sn,
                attr=attr,
                vsize=vsize,
                vfree=vfree))

        for entry in self.get_cmd_output(['lvdisplay', '-C', '--noheadings', '--separator', r':'], ':', 12):
            lv, vg, attr, lsize, pool, origin, data, meta, move, log, cpy_sync, convert = entry
            result.lvdisplay.append(LvdisplayEntry(
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
                convert=convert))

        for entry in self.get_cmd_output(['systemd-mount', '--list'], ' ', 7):
            # We need to filter the entry because there is a ton of whitespace.
            node, path, model, wwn, fs_type, label, uuid = list(filter(lambda x: x != '', entry))
            if node == "NODE":
                # First row of the "systemd-mount --list" output is a header.
                # Just skip it.
                continue
            result.systemdmount.append(SystemdMountEntry(
                node=node,
                path=path,
                model=model,
                wwn=wwn,
                fs_type=fs_type,
                label=label,
                uuid=uuid))

        self.produce(result)
