from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class PartitionEntry(Model):
    topic = SystemInfoTopic

    major = fields.String()
    minor = fields.String()
    blocks = fields.String()
    name = fields.String()


class FstabEntry(Model):
    topic = SystemInfoTopic

    fs_spec = fields.String()
    fs_file = fields.String()
    fs_vfstype = fields.String()
    fs_mntops = fields.String()
    fs_freq = fields.String()
    fs_passno = fields.String()


class MountEntry(Model):
    topic = SystemInfoTopic

    name = fields.String()
    mount = fields.String()
    tp = fields.String()
    options = fields.String()


class LsblkEntry(Model):
    topic = SystemInfoTopic

    name = fields.String()
    kname = fields.String()
    maj_min = fields.String()
    rm = fields.String()
    size = fields.String()
    bsize = fields.Integer()
    ro = fields.String()
    tp = fields.String()
    mountpoint = fields.String()


class PvsEntry(Model):
    topic = SystemInfoTopic

    pv = fields.String()
    vg = fields.String()
    fmt = fields.String()
    attr = fields.String()
    psize = fields.String()
    pfree = fields.String()


class VgsEntry(Model):
    topic = SystemInfoTopic

    vg = fields.String()
    pv = fields.String()
    lv = fields.String()
    sn = fields.String()
    attr = fields.String()
    vsize = fields.String()
    vfree = fields.String()


class LvdisplayEntry(Model):
    topic = SystemInfoTopic

    lv = fields.String()
    vg = fields.String()
    attr = fields.String()
    lsize = fields.String()
    pool = fields.String()
    origin = fields.String()
    data = fields.String()
    meta = fields.String()
    move = fields.String()
    log = fields.String()
    cpy_sync = fields.String()
    convert = fields.String()


class SystemdMountEntry(Model):
    topic = SystemInfoTopic

    node = fields.String()
    path = fields.String()
    model = fields.String()
    wwn = fields.String()
    fs_type = fields.String()
    label = fields.String()
    uuid = fields.String()


class StorageInfo(Model):
    topic = SystemInfoTopic
    partitions = fields.List(fields.Model(PartitionEntry), default=[])
    fstab = fields.List(fields.Model(FstabEntry), default=[])
    mount = fields.List(fields.Model(MountEntry), default=[])
    lsblk = fields.List(fields.Model(LsblkEntry), default=[])
    pvs = fields.List(fields.Model(PvsEntry), default=[])
    vgs = fields.List(fields.Model(VgsEntry), default=[])
    lvdisplay = fields.List(fields.Model(LvdisplayEntry), default=[])
    systemdmount = fields.List(fields.Model(SystemdMountEntry), default=[])
