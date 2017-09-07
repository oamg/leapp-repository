from leapp.models import Model, fields
from leapp.topics import SystemInfoTopic


class PartitionEntry(Model):
    topic = SystemInfoTopic

    major = fields.String(required=True)
    minor = fields.String(required=True)
    blocks = fields.String(required=True)
    name = fields.String(required=True)


class FstabEntry(Model):
    topic = SystemInfoTopic

    fs_spec = fields.String(required=True)
    fs_file = fields.String(required=True)
    fs_vfstype = fields.String(required=True)
    fs_mntops = fields.String(required=True)
    fs_freq = fields.String(required=True)
    fs_passno = fields.String(required=True)


class MountEntry(Model):
    topic = SystemInfoTopic

    name = fields.String(required=True)
    mount = fields.String(required=True)
    tp = fields.String(required=True)
    options = fields.String(required=True)


class LsblkEntry(Model):
    topic = SystemInfoTopic

    name = fields.String(required=True)
    maj_min = fields.String(required=True)
    rm = fields.String(required=True)
    size = fields.String(required=True)
    ro = fields.String(required=True)
    tp = fields.String(required=True)
    mountpoint = fields.String(required=True)


class PvsEntry(Model):
    topic = SystemInfoTopic

    pv = fields.String(required=True)
    vg = fields.String(required=True)
    fmt = fields.String(required=True)
    attr = fields.String(required=True)
    psize = fields.String(required=True)
    pfree = fields.String(required=True)


class VgsEntry(Model):
    topic = SystemInfoTopic

    vg = fields.String(required=True)
    pv = fields.String(required=True)
    lv = fields.String(required=True)
    sn = fields.String(required=True)
    attr = fields.String(required=True)
    vsize = fields.String(required=True)
    vfree = fields.String(required=True)


class LvdisplayEntry(Model):
    topic = SystemInfoTopic

    lv = fields.String(required=True)
    vg = fields.String(required=True)
    attr = fields.String(required=True)
    lsize = fields.String(required=True)
    pool = fields.String(required=True)
    origin = fields.String(required=True)
    data = fields.String(required=True)
    meta = fields.String(required=True)
    move = fields.String(required=True)
    log = fields.String(required=True)
    cpy_sync = fields.String(required=True)
    convert = fields.String(required=True)


class StorageInfo(Model):
    topic = SystemInfoTopic
    partitions = fields.List(fields.Model(PartitionEntry), required=True, default=[])
    fstab = fields.List(fields.Model(FstabEntry), required=True, default=[])
    mount = fields.List(fields.Model(MountEntry), required=True, default=[])
    lsblk = fields.List(fields.Model(LsblkEntry), required=True, default=[])
    pvs = fields.List(fields.Model(PvsEntry), required=True, default=[])
    vgs = fields.List(fields.Model(VgsEntry), required=True, default=[])
    lvdisplay = fields.List(fields.Model(LvdisplayEntry), required=True, default=[])
