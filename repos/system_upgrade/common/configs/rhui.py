"""
Configuration keys for RHUI.

In case of RHUI in private regions it usual that publicly known RHUI data
is not valid. In such cases it's possible to provide the correct expected
RHUI data to correct the in-place upgrade process.
"""

from leapp.actors.config import Config
from leapp.models import fields

RHUI_CONFIG_SECTION = 'rhui'


# @Note(mhecko): We use to distinguish config instantiated from default values that we should ignore
# #              Maybe we could make all config values None and detect it that way, but then we cannot
# #              give the user an example how the config should look like.
class RhuiUseConfig(Config):
    section = RHUI_CONFIG_SECTION
    name = "use_config"
    type_ = fields.Boolean()
    default = False
    description = """
        Use values provided in the configuration file to override leapp's decisions.
    """


class RhuiSourcePkgs(Config):
    section = RHUI_CONFIG_SECTION
    name = "source_clients"
    type_ = fields.List(fields.String())
    default = []
    description = """
        The name of the source RHUI client RPMs (to be removed from the system).
    """


class RhuiTargetPkgs(Config):
    section = RHUI_CONFIG_SECTION
    name = "target_clients"
    type_ = fields.List(fields.String())
    default = []
    description = """
        The name of the target RHUI client RPM (to be installed on the system).
    """


class RhuiCloudProvider(Config):
    section = RHUI_CONFIG_SECTION
    name = "cloud_provider"
    type_ = fields.String()
    default = ""
    description = """
        Cloud provider name that should be used internally by leapp.

        Leapp recognizes the following cloud providers:
            - azure
            - aws
            - google

        Cloud provider information is used for triggering some provider-specific modifications. The value also
        influences how leapp determines target repositories to enable.
    """


# @Note(mhecko): We likely don't need this. We need the variant primarily to grab files from a correct directory
# in leapp-rhui-<provider> folders.
class RhuiCloudVariant(Config):
    section = RHUI_CONFIG_SECTION
    name = "image_variant"
    type_ = fields.String()
    default = "ordinary"
    description = """
        RHEL variant of the source system - is the source system SAP-specific image?

        Leapp recognizes the following cloud providers:
            - ordinary    # The source system has not been deployed from a RHEL with SAP image
            - sap         # RHEL SAP images
            - sap-apps    # RHEL SAP Apps images (Azure only)
            - sap-ha      # RHEL HA Apps images (HA only)

        Cloud provider information is used for triggering some provider-specific modifications. The value also
        influences how leapp determines target repositories to enable.

        Default:
            "ordinary"
    """


class RhuiUpgradeFiles(Config):
    section = RHUI_CONFIG_SECTION
    name = "upgrade_files"
    type_ = fields.StringMap(fields.String())
    default = dict()
    description = """
        A mapping from source file paths to the destination where should they be
        placed in the upgrade container.

        Typically, these files should be provided by leapp-rhui-<PROVIDER> packages.

        These files are needed to facilitate access to target repositories. Typical examples are: repofile(s),
        certificates and keys.
    """


class RhuiTargetRepositoriesToUse(Config):
    section = RHUI_CONFIG_SECTION
    name = "rhui_target_repositories_to_use"
    type_ = fields.List(fields.String())
    description = """
        List of target repositories enabled during the upgrade. Similar to executing leapp with --enablerepo.

        The repositories to be enabled need to be either in the repofiles listed in the `upgrade_files` field,
        or in repofiles present on the source system.
    """
    default = list()


all_rhui_cfg = (
    RhuiTargetPkgs,
    RhuiUpgradeFiles,
    RhuiTargetRepositoriesToUse,
    RhuiCloudProvider,
    RhuiCloudVariant,
    RhuiSourcePkgs,
    RhuiUseConfig
)
