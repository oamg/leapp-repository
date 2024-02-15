from leapp.models import CopyFile, fields, Model
from leapp.topics import SystemInfoTopic


class TargetRHUIPreInstallTasks(Model):
    """Tasks required to be executed before target RHUI clients are installed"""
    topic = SystemInfoTopic

    files_to_remove = fields.List(fields.String(), default=[])
    """Files to remove from the source system in order to setup target RHUI access"""

    files_to_copy_into_overlay = fields.List(fields.Model(CopyFile), default=[])
    """Files to copy into the scratch (overlayfs) container in order to setup target RHUI access"""


class TargetRHUIPostInstallTasks(Model):
    """Tasks required to be executed after target RHUI clients are installed to facilitate access to target content."""
    topic = SystemInfoTopic

    files_to_copy = fields.List(fields.Model(CopyFile), default=[])
    """Source and destination are paths inside the container"""


class TargetRHUISetupInfo(Model):
    topic = SystemInfoTopic

    enable_only_repoids_in_copied_files = fields.Boolean(default=True)
    """If True (default) only the repoids from copied files will be enabled during client installation"""

    preinstall_tasks = fields.Model(TargetRHUIPreInstallTasks)
    """Tasks that must be performed before attempting to install the target client(s)"""

    postinstall_tasks = fields.Model(TargetRHUIPostInstallTasks)
    """Tasks that must be performed after the target client is installed (before any other content is accessed)"""

    files_supporting_client_operation = fields.List(fields.String(), default=[])
    """A subset of files copied in preinstall tasks that should not be cleaned up."""

    bootstrap_target_client = fields.Boolean(default=True)
    """
    Swap the current RHUI client for the target one to facilitate access to the target content.

    When False, only files from the leapp-rhui-<provider> will be used to access target content.
    """


class RHUIInfo(Model):
    """
    Facts about public cloud variant and RHUI infrastructure
    """
    topic = SystemInfoTopic

    provider = fields.String()
    """Provider name"""

    variant = fields.StringEnum(['ordinary', 'sap', 'sap-apps', 'sap-ha'], default='ordinary')
    """Variant of the system"""

    src_client_pkg_names = fields.List(fields.String())
    """Names of the RHUI client packages providing repofiles to the source system"""

    target_client_pkg_names = fields.List(fields.String())
    """Names of the RHUI client packages providing repofiles to the target system"""

    target_client_setup_info = fields.Model(TargetRHUISetupInfo)
