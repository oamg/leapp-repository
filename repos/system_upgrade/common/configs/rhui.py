"""
Configuration keys for RHUI.

In case of RHUI in private regions it usual that publicly known RHUI data
is not valid. In such cases it's possible to provide the correct expected
RHUI data to correct the in-place upgrade process.
"""

from leapp.models import fields
from leapp.models.configs import Config


class RhuiSrcPkg(Config):
    section = "rhui"
    name = "src_pkg"
    type_ = fields.String(default="rhui")
    description = """
        The name of the source RHUI client RPM (installed on the system).
        Default: rhui.
    """


class RhuiTargetPkg(Config):
    section = "rhui"
    name = "target_pkg"
    type_ = fields.String(default="rhui")
    description = """
        The name of the target RHUI client RPM (to be installed on the system).
        Default: rhui
    """


class RhuiLeappRhuiPkg(Config):
    section = "rhui"
    name = "leapp_rhui_pkg"
    type_ = fields.String(default="leapp-rhui")
    description = """
    The name of the leapp-rhui RPM.  Default: leapp-rhui
    """


class RhuiLeappRhuiPkgRepo(Config):
    section = "rhui"
    name = "leapp_rhui_pkg_repo"
    type_ = fields.String(default="rhel-base")
    description = """
        The repository ID containing the specified leapp-rhui RPM.
        Default: rhel-base
    """

all_rhui_cfg = (RhuiSrcPkg, RhuiTargetPkg, RhuiLeappRhuiPkg, RhuiLeappRhuiPkg)
# Usage: from configs import rhui
#        class MyActor:
#            [...]
#            configs = all_rhui_cfg + (MyConfig,)

### We need to implement fields.Map before this can be enabled
'''
class RhuiFileMap(Config):
    section = "rhui"
    name = "file_map"
    type_ = fields.Map(fields.String())
    description = """
        Define directories to which paritcular files provided by the leapp-rhui
        RPM should be installed. The files in 'files_map' are provided by
        special Leapp rpms (per cloud) and are supposed to be delivered into the
        repos/system_upgrade/common/files/rhui/<PROVIDER> directory.

        These files are usually needed to get access to the target system repositories
        using RHUI. Typically these are certificates, keys, and repofiles with the
        target RHUI repositories.

        The key is the name of the file, the value is the expected directory
        where the file should be installed on the upgraded system.
    """
'''
