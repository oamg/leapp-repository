from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class XFSInfoSection(Model):
    """
    Represents a section of `xfs_info`.
    """

    topic = SystemInfoTopic


class XFSInfoMetaData(XFSInfoSection):
    """
    Represents the `meta-data` section of `xfs_info`.
    """

    device = fields.String()
    bigtime = fields.Nullable(fields.String())
    crc = fields.Nullable(fields.String())

    # NOTE(dkubek): meta-data section might also contain the following fields
    # which are not being used right now

    # isize = fields.String()
    # agcount = fields.String()
    # agsize = fields.String()
    # sectsz = fields.String()
    # attr = fields.String()
    # projid32bit = fields.String()
    # finobt = fields.String()
    # sparse = fields.String()
    # rmapbt = fields.String()
    # reflink = fields.String()
    # inobtcount = fields.String()
    # nrext64 = fields.String()


class XFSInfoData(XFSInfoSection):
    """
    Represents the `data` section of `xfs_info`.
    """

    bsize = fields.String()
    blocks = fields.String()

    # NOTE(dkubek): data section might also contain the following fields
    # which are not being used right now

    # imaxpct = fields.String()
    # sunit = fields.String()
    # swidth = fields.String()


class XFSInfoNaming(XFSInfoSection):
    """
    Represents the `naming` section of `xfs_info`.
    """

    ftype = fields.Nullable(fields.String())

    # NOTE(dkubek): naming section might also contain the following fields
    # which are not being used right now

    # version = fields.String()
    # bsize = fields.String()
    # ascii_ci = fields.String()


class XFSInfoLog(XFSInfoSection):
    """
    Represents the `log` section of `xfs_info`.
    """

    bsize = fields.String()
    blocks = fields.String()

    # NOTE(dkubek): log section might also contain the following fields
    # which are not being used right now

    # internal = fields.String()
    # version = fields.String()
    # sectsz = fields.String()
    # sunit = fields.String()
    # lazy_count = fields.String()


class XFSInfoRealtime(XFSInfoSection):
    """
    Represents the `realtime` section of `xfs_info`.
    """

    # NOTE(dkubek): realtime section might also contain the following fields
    # which are not being used right now

    # extsz = fields.String()
    # blocks = fields.String()
    # rtextents = fields.String()


class XFSInfo(Model):
    """
    A message containing the parsed results from `xfs_info` command for given mountpoint.

    Attributes are stored as key-value pairs. Optional section attribute is
    stored under the identifier 'specifier'.
    """
    topic = SystemInfoTopic

    mountpoint = fields.String()
    """
    Mountpoint containing the XFS filesystem.
    """

    meta_data = fields.Model(XFSInfoMetaData)
    """
    Attributes of 'meta-data' section.
    """

    data = fields.Model(XFSInfoData)
    """
    Attributes of 'data' section.
    """

    naming = fields.Model(XFSInfoNaming)
    """
    Attributes of 'naming' section.
    """

    log = fields.Model(XFSInfoLog)
    """
    Attributes of 'log' section.
    """

    realtime = fields.Model(XFSInfoRealtime)
    """
    Attributes of 'realtime' section.
    """


class XFSInfoFacts(Model):
    """
    Message containing the xfs info for all mounted XFS filesystems.
    """
    topic = SystemInfoTopic

    mountpoints = fields.List(fields.Model(XFSInfo))
