from leapp.models import fields, Model
from leapp.topics import BootPrepTopic, TargetUserspaceTopic, TransactionTopic
from leapp.utils.deprecation import deprecated


class TargetUserSpaceInfo(Model):
    """
    Information about the target userspace container to be able to use it

    The target userspace container contains the most crucial part of the target
    system to be able to proceed the inplace upgrade process (let's simplify
    it, and call it bootstrap of the target system). It contains (e.g.) the
    package manager of the target system, so we can calculate and process
    the RPM transaction. Additionally, it is used to create the upgrade
    initramfs (see the UpgradeInitramfsTasks model for more information).

    See the TargetUserSpaceTasks model for possibilities to influence content
    of the container automatically.
    """
    topic = TransactionTopic

    path = fields.String()
    """
    Path to the created target userspace directory

    It could be used as a container. It contains top level rootfs
    directories (bin, usr, var, ...).
    """

    scratch = fields.String()
    """
    Path to the directory with stored xfs-ftype workaround files

    It's not possible to create overlayfs over XFS without the ftype attribute.
    To workaround this problem, we are creating these files with EXT4 FS
    inside.
    """

    mounts = fields.String()
    """
    Path to the directory with additional mountpoints for the target userspace
    container.

    E.g. the overlayfss of the host filesystems can be stored here.
    """


class CopyFile(Model):
    """
    Specify a file that should be copied from the host to the target userspace
    container
    """
    topic = TransactionTopic

    src = fields.String()
    """
    Cannonical path to the file (on the host) that should be copied
    """

    dst = fields.Nullable(fields.String())
    """
    The path inside the target userspace container where the file should
    be copied.

    Do not add the path to the container itself. E.g. when the file should be
    installed into /etc/myconf in the container context, set /etc/myconf,
    not /path/to/container/etc/myconf.

    If dst is not set, the path inside the container is same as on the host.
    """


class TargetUserSpacePreupgradeTasks(Model):
    """
    Influence content of the target userspace container

    See the TargetUserSpaceInfo model description for more info about the
    target userspace container.
    """
    topic = TransactionTopic

    copy_files = fields.List(fields.Model(CopyFile), default=[])
    """
    List of files on the host that should be copied into the container

    Directories are supported as well.

    If a file/dir already exists on the destination path, it is removed &
    replaced.
    """

    install_rpms = fields.List(fields.String(), default=[])
    """
    List of rpm names that are required to be installed when the container
    is created.
    """


class TargetUserSpaceUpgradeTasks(TargetUserSpacePreupgradeTasks):
    """
    Analogy to the TargetUserSpacePreupgradeTasks model, but focused
    on initramfs requirements.

    Generate this message to ensure all RPMs and configuration files, needed
    to be able to generate the upgrade initramfs (see UpgradeInitramfsTasks),
    are available inside the container.

    For performance reasons (do not download & install bunch of rpms before
    it's sure the upgrade is not inhibited) these tasks are executed just
    in time it's 'sure' the upgrade is going to happen.
    """


@deprecated(since='2021-10-10', message='Replaced by TargetUserSpacePreupgradeTasks.')
class RequiredTargetUserspacePackages(Model):
    topic = TargetUserspaceTopic
    packages = fields.List(fields.String(), default=[])


@deprecated(since='2021-10-10', message='Replaced by TargetUserSpaceInitrdEnvTasks')
class RequiredUpgradeInitramPackages(Model):
    """
    Requests packages to be installed so that the leapp upgrade dracut image generation will succeed
    """
    topic = BootPrepTopic

    packages = fields.List(fields.String(), default=[])
    """
    List of packages names to install on the target userspace so their content can be included in the initram disk
    """
