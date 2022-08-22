from leapp.models import fields, Model
from leapp.topics import BootPrepTopic, SystemInfoTopic
from leapp.utils.deprecation import deprecated


class DracutModule(Model):
    """
    Specify a dracut module that should be included into the initramfs

    The specified dracut module has to be compatible with the target system.

    See the description of UpgradeInitramfsTasks and TargetInitramfsTasks
    for more information about the role of initramfs in the in-place upgrade
    process.
    """
    topic = BootPrepTopic

    name = fields.String()
    """
    Name of the dracut module that should be added (--add option of dracut)
    when a initramfs is built.
    """

    module_path = fields.Nullable(fields.String(default=None))
    """
    module_path specifies dracut modules that are supposed to be copied

    If the path is not set, the given name will just be activated. IOW,
    if the dracut module is stored outside the /usr/lib/dracut/modules.d/
    directory, set the absolute path to it, so leapp will manage it during
    the upgrade to ensure the module will be added into the initramfs.

    The module has to be stored on the local storage. In such a case, it is
    recommended to store it into the 'files' directory of an actor generating
    this object.

    Note: It's expected to set the full path from the host POV. In case
    of actions inside containers, the module is still copied from the HOST
    into the container workspace.
    """


class UpgradeInitramfsTasks(Model):
    """
    Influence generating of the (leapp) upgrade initramfs

    The upgrade initramfs is used during the crucial part of the upgrade,
    in which the original rpms are upgraded, configuration of applications
    are migrated, etc. To be able to boot into the leapp upgrade environment
    correctly, it is expected all needed drivers, configuration files, ... are
    included inside the upgrade initramfs. Produce this message with
    expected content to influence the upgrade initramfs.

    If some specific rpms or content is required to be able to build the
    upgrade initramfs, see the <container-model>.

    Note: The built initramfs is composed of stuff for the target system.
    In example, if you are on RHEL 7 and plan the upgrade to RHEL 8, you need
    to provide content (e.g. drivers, dracut modules) compatible with
    RHEL 8 system.
    """
    topic = BootPrepTopic

    include_files = fields.List(fields.String(), default=[])
    """
    List of files (cannonical filesystem paths) to include in the initramfs
    """

    include_dracut_modules = fields.List(fields.Model(DracutModule), default=[])
    """
    List of dracut modules that should be installed in the initramfs.

    See the DracutModule model for more information.
    """


class TargetInitramfsTasks(UpgradeInitramfsTasks):
    """
    Analogy to UpgradeInitramfsTasks, but referring to the target initram disk.

    Target initramfs is the one, that will be used to boot to your upgraded
    system. If you want to ensure that you are able to boot into the target
    (upgraded) system, it is possible you need to add same stuff as you added
    into the upgrade initramfs.

    If some specific rpms are required to be able to build the upgrade
    initramfs, install these via the RpmTransactionTasks model.
    """


@deprecated(since='2021-10-10', message='Replaced by TargetInitramfsTasks.')
class InitrdIncludes(Model):
    """
    List of files (cannonical filesystem paths) to include in RHEL-8 initramfs
    """
    topic = SystemInfoTopic

    files = fields.List(fields.String())


@deprecated(since='2021-10-10', message='Replaced by UpgradeInitramfsTasks.')
class UpgradeDracutModule(Model):
    """
    Specify a dracut module that should be included into the (leapp) upgrade initramfs.

    The upgrade initramfs is used during the crucial part of the upgrade,
    in which the original rpms are upgraded. If a dracut module is required to
    be included inside the upgrade initramfs (e.g. because it is needed
    to handle/initialize your storage properly), produce this msg.
    """
    topic = BootPrepTopic

    name = fields.String()
    """
    Name of the dracut module that should be added (--add option of dracut)
    """

    module_path = fields.Nullable(fields.String(default=None))
    """
    module_path specifies dracut modules that are to be copied

    If the path is not set, the given name will just be activated.
    """
