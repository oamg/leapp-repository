import os
from collections import namedtuple

from leapp.libraries.common.config import architecture as arch
from leapp.libraries.common.config.version import get_source_major_version, get_target_major_version

DNF_PLUGIN_PATH_PY2 = '/usr/lib/python2.7/site-packages/dnf-plugins/'
YUM_REPOS_PATH = '/etc/yum.repos.d'

RHUI_PKI_DIR = '/etc/pki/rhui'
RHUI_PKI_PRODUCT_DIR = os.path.join(RHUI_PKI_DIR, 'product')
RHUI_PKI_PRIVATE_DIR = os.path.join(RHUI_PKI_DIR, 'private')

AWS_DNF_PLUGIN_NAME = 'amazon-id.py'


class ContentChannel(object):
    GA = 'ga'
    TUV = 'tuv'
    E4S = 'e4s'
    EUS = 'eus'
    AUS = 'aus'
    BETA = 'beta'


class RHUIVariant(object):
    ORDINARY = 'ordinary'  # Special value - not displayed in report/errors
    SAP = 'sap'
    SAP_APPS = 'sap-apps'
    SAP_HA = 'sap-ha'


class RHUIProvider(object):
    GOOGLE = 'Google'
    AZURE = 'Azure'
    AWS = 'AWS'
    ALIBABA = 'Alibaba'


# The files in 'files_map' are provided by special Leapp rpms (per cloud) and
# are delivered into "repos/system_upgrade/common/files/rhui/<PROVIDER>

RHUISetup = namedtuple(
    'RHUISetup',
    ('clients', 'leapp_pkg', 'mandatory_files', 'optional_files', 'extra_info', 'os_version',
     'arch', 'content_channel', 'files_supporting_client_operation')
)
"""RHUI-Setup-specific details used during IPU
.. py:attribute:: clients
    A set of RHUI clients present on the system.
.. py:attribute:: leapp_pkg
    The name of leapp's rhui-specific pkg providing repofiles, certs and keys to access package of the setup.
.. py:attribute:: mandatory_files
    Mandatory files and their destinations to copy into target userspace container required to access the target OS
    content. If not present, an exception will be raised.
.. py:attribute:: optional_files
    Optional files and their destinations to copy into target userspace container required to access the target OS
    content. Nonexistence of any of these files is ignored.
.. py:attribute:: extra_info
    Extra information about the setup.
.. py:attribute:: os_version
    The major OS version of the RHUI system.
.. py:attribute:: content_channel
    Content channel used by the RHUI setup.
.. py:attribute:: files_supporting_client_operation
    A subset of files from ``mandatory_files`` that are necessary for client to work (cannot be cleaned up).
"""


class RHUIFamily(object):
    def __init__(self, provider, client_files_folder='', variant=RHUIVariant.ORDINARY, arch=arch.ARCH_X86_64,):
        self.provider = provider
        self.client_files_folder = client_files_folder
        self.variant = variant
        self.arch = arch

    def __hash__(self):
        return hash((self.provider, self.variant, self.arch))

    def __eq__(self, other):
        if not isinstance(other, RHUIFamily):
            return False
        self_repr = (self.provider, self.variant, self.arch)
        other_repr = (other.provider, other.variant, other.arch)
        return self_repr == other_repr

    def full_eq(self, other):
        partial_eq = self == other
        return partial_eq and self.client_files_folder == other.client_files_folder

    def __str__(self):
        template = 'RHUIFamily(provider={provider}, variant={variant}, arch={arch})'
        return template.format(provider=self.provider, variant=self.variant, arch=self.arch)


def mk_rhui_setup(clients=None, leapp_pkg='', mandatory_files=None, optional_files=None,
                  extra_info=None, os_version='8.0', arch=arch.ARCH_X86_64, content_channel=ContentChannel.GA,
                  files_supporting_client_operation=None):

    os_version_fragments = os_version.split('.')
    if len(os_version_fragments) == 1:
        os_version_tuple = (int(os_version), 0)
    else:
        os_version_tuple = (int(os_version_fragments[0]), int(os_version_fragments[1]))

    clients = clients or set()
    mandatory_files = mandatory_files or []
    extra_info = extra_info or {}
    files_supporting_client_operation = files_supporting_client_operation or []

    # Since the default optional files are not [], we cannot use the same construction as above
    # to allow the caller to specify empty optional files
    default_opt_files = [('content-leapp.crt', RHUI_PKI_PRODUCT_DIR), ('key-leapp.pem', RHUI_PKI_DIR)]
    optional_files = default_opt_files if optional_files is None else optional_files

    return RHUISetup(clients=clients, leapp_pkg=leapp_pkg, mandatory_files=mandatory_files, arch=arch,
                     content_channel=content_channel, optional_files=optional_files, extra_info=extra_info,
                     os_version=os_version_tuple, files_supporting_client_operation=files_supporting_client_operation)


# This will be the new "cloud map". Essentially a directed graph with edges defined implicitly by OS versions +
# setup family identification. In theory, we can make the variant be part of rhui setups, but this way we don't
# have to repeatedly write it to every known setup there is (a sort of compression). Furthermore, it limits
# the search for target equivalent to setups sharing the same family, and thus reducing a chance of error.
RHUI_SETUPS = {
    RHUIFamily(RHUIProvider.AWS, client_files_folder='aws'): [
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-8.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-8.key', RHUI_PKI_DIR),
                        (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      files_supporting_client_operation=[AWS_DNF_PLUGIN_NAME],
                      optional_files=[
                        ('content-rhel8.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel8.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='8'),
        # @Note(mhecko): We don't need to deal with AWS_DNF_PLUGIN_NAME here as on rhel8+ we can use the plugin
        # #              provided by the target client - there is no Python2 incompatibility issue there.
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-9.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-9.key', RHUI_PKI_DIR),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel9.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel9.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='9'),
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-10.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-10.key', RHUI_PKI_DIR),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel10.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel10.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='10'),
    ],
    RHUIFamily(RHUIProvider.AWS, arch=arch.ARCH_ARM64, client_files_folder='aws'): [
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-8.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-8.key', RHUI_PKI_DIR),
                        (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      files_supporting_client_operation=[AWS_DNF_PLUGIN_NAME],
                      optional_files=[
                        ('content-rhel8.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel8.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='8', arch=arch.ARCH_ARM64),
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-9.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-9.key', RHUI_PKI_DIR),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel9.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel9.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='9', arch=arch.ARCH_ARM64),
        mk_rhui_setup(clients={'rh-amazon-rhui-client'}, leapp_pkg='leapp-rhui-aws',
                      mandatory_files=[
                        ('rhui-client-config-server-10.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-10.key', RHUI_PKI_DIR),
                        ('leapp-aws.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel10.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel10.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='10'),
    ],
    RHUIFamily(RHUIProvider.AWS, variant=RHUIVariant.SAP, client_files_folder='aws-sap-e4s'): [
        mk_rhui_setup(clients={'rh-amazon-rhui-client-sap-bundle-e4s'}, leapp_pkg='leapp-rhui-aws-sap-e4s',
                      mandatory_files=[
                        ('rhui-client-config-server-8-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-8-sap-bundle.key', RHUI_PKI_DIR),
                        ('content-rhel8-sap-bundle-e4s.crt', RHUI_PKI_PRODUCT_DIR),
                        ('content-rhel8-sap-bundle-e4s.key', RHUI_PKI_DIR),
                        (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                        ('leapp-aws-sap-e4s.repo', YUM_REPOS_PATH)
                      ],
                      files_supporting_client_operation=[AWS_DNF_PLUGIN_NAME],
                      optional_files=[
                        ('content-rhel8-sap.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel8-sap.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='8', content_channel=ContentChannel.E4S),
        mk_rhui_setup(clients={'rh-amazon-rhui-client-sap-bundle'}, leapp_pkg='leapp-rhui-aws-sap-e4s',
                      mandatory_files=[
                        ('rhui-client-config-server-8-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-8-sap-bundle.key', RHUI_PKI_DIR),
                        ('content-rhel8-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                        ('content-rhel8-sap-bundle.key', RHUI_PKI_DIR),
                        (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                        ('leapp-aws-sap.repo', YUM_REPOS_PATH)
                      ],
                      files_supporting_client_operation=[AWS_DNF_PLUGIN_NAME],
                      optional_files=[
                        ('content-rhel8-sap.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel8-sap.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='8.10'),
        mk_rhui_setup(clients={'rh-amazon-rhui-client-sap-bundle-e4s'}, leapp_pkg='leapp-rhui-aws-sap-e4s',
                      mandatory_files=[
                        ('rhui-client-config-server-9-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-9-sap-bundle.key', RHUI_PKI_DIR),
                        ('leapp-aws-sap-e4s.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel9-sap-bundle-e4s.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel9-sap-bundle-e4s.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='9', content_channel=ContentChannel.E4S),
        mk_rhui_setup(clients={'rh-amazon-rhui-client-sap-bundle-e4s'}, leapp_pkg='leapp-rhui-aws-sap-e4s',
                      mandatory_files=[
                        ('rhui-client-config-server-10-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                        ('rhui-client-config-server-10-sap-bundle.key', RHUI_PKI_DIR),
                        ('leapp-aws-sap-e4s.repo', YUM_REPOS_PATH)
                      ],
                      optional_files=[
                        ('content-rhel10-sap-bundle-e4s.key', RHUI_PKI_DIR),
                        ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                        ('content-rhel10-sap-bundle-e4s.crt', RHUI_PKI_PRODUCT_DIR)
                      ], os_version='10', content_channel=ContentChannel.E4S),
    ],
    RHUIFamily(RHUIProvider.AZURE, client_files_folder='azure'): [
        mk_rhui_setup(clients={'rhui-azure-rhel8'}, leapp_pkg='leapp-rhui-azure',
                      mandatory_files=[('leapp-azure.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='8'),
        mk_rhui_setup(clients={'rhui-azure-rhel9'}, leapp_pkg='leapp-rhui-azure',
                      mandatory_files=[('leapp-azure.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='9'),
        mk_rhui_setup(clients={'rhui-azure-rhel10'}, leapp_pkg='leapp-rhui-azure',
                      mandatory_files=[
                          ('leapp-azure.repo', YUM_REPOS_PATH),
                          # We need to have the new GPG key ready when we will be bootstrapping
                          # target rhui client.
                          ('RPM-GPG-KEY-microsoft-azure-release-new', '/etc/pki/rpm-gpg/')
                      ],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='10'),
    ],
    RHUIFamily(RHUIProvider.AZURE, variant=RHUIVariant.SAP_APPS, client_files_folder='azure-sap-apps'): [
        mk_rhui_setup(clients={'rhui-azure-rhel8-sapapps'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-sap-apps.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sapapps.pem', RHUI_PKI_DIR),
                        ('content-sapapps.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='8', content_channel=ContentChannel.EUS),
        mk_rhui_setup(clients={'rhui-azure-rhel8-base-sap-apps'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-base-sap-apps.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sapapps.pem', RHUI_PKI_DIR),
                        ('content-sapapps.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='8.10', content_channel=ContentChannel.GA),
        mk_rhui_setup(clients={'rhui-azure-rhel9-sapapps'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-sap-apps.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sapapps.pem', RHUI_PKI_DIR),
                        ('content-sapapps.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='9', content_channel=ContentChannel.EUS),
        mk_rhui_setup(clients={'rhui-azure-rhel10-sapapps'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[
                          ('leapp-azure-sap-apps.repo', YUM_REPOS_PATH),
                          ('RPM-GPG-KEY-microsoft-azure-release-new', '/etc/pki/rpm-gpg/')
                      ],
                      optional_files=[
                        ('key-sapapps.pem', RHUI_PKI_DIR),
                        ('content-sapapps.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='10', content_channel=ContentChannel.EUS),
    ],
    RHUIFamily(RHUIProvider.AZURE, variant=RHUIVariant.SAP_HA, client_files_folder='azure-sap-ha'): [
        mk_rhui_setup(clients={'rhui-azure-rhel8-sap-ha'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-sap-ha.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sap-ha.pem', RHUI_PKI_DIR),
                        ('content-sap-ha.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='8', content_channel=ContentChannel.E4S),
        mk_rhui_setup(clients={'rhui-azure-rhel8-base-sap-ha'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-base-sap-ha.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sap-ha.pem', RHUI_PKI_DIR),
                        ('content-sap-ha.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='8.10'),
        mk_rhui_setup(clients={'rhui-azure-rhel9-sap-ha'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[('leapp-azure-sap-ha.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key-sap-ha.pem', RHUI_PKI_DIR),
                        ('content-sap-ha.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='9', content_channel=ContentChannel.E4S),
        mk_rhui_setup(clients={'rhui-azure-rhel10-sap-ha'}, leapp_pkg='leapp-rhui-azure-sap',
                      mandatory_files=[
                          ('leapp-azure-sap-ha.repo', YUM_REPOS_PATH),
                          ('RPM-GPG-KEY-microsoft-azure-release-new', '/etc/pki/rpm-gpg/')
                      ],
                      optional_files=[
                        ('key-sap-ha.pem', RHUI_PKI_DIR),
                        ('content-sap-ha.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      extra_info={'agent_pkg': 'WALinuxAgent'},
                      os_version='10', content_channel=ContentChannel.E4S),
    ],
    RHUIFamily(RHUIProvider.GOOGLE, client_files_folder='google'): [
        mk_rhui_setup(clients={'google-rhui-client-rhel8'}, leapp_pkg='leapp-rhui-google',
                      mandatory_files=[('leapp-google.repo', YUM_REPOS_PATH)],
                      files_supporting_client_operation=['leapp-google.repo'],
                      os_version='8'),
        mk_rhui_setup(clients={'google-rhui-client-rhel9'}, leapp_pkg='leapp-rhui-google',
                      mandatory_files=[('leapp-google.repo', YUM_REPOS_PATH)],
                      files_supporting_client_operation=['leapp-google.repo'],
                      os_version='9'),
    ],
    RHUIFamily(RHUIProvider.GOOGLE, variant=RHUIVariant.SAP, client_files_folder='google-sap'): [
        mk_rhui_setup(clients={'google-rhui-client-rhel8-sap'}, leapp_pkg='leapp-rhui-google-sap',
                      mandatory_files=[('leapp-google-sap.repo', YUM_REPOS_PATH)],
                      files_supporting_client_operation=['leapp-google-sap.repo'],
                      os_version='8', content_channel=ContentChannel.E4S),
        mk_rhui_setup(clients={'google-rhui-client-rhel810-sap'}, leapp_pkg='leapp-rhui-google-sap',
                      mandatory_files=[('leapp-google-sap.repo', YUM_REPOS_PATH)],
                      files_supporting_client_operation=['leapp-google-sap.repo'],
                      os_version='8.10', content_channel=ContentChannel.GA),
        mk_rhui_setup(clients={'google-rhui-client-rhel9-sap'}, leapp_pkg='leapp-rhui-google-sap',
                      mandatory_files=[('leapp-google-sap.repo', YUM_REPOS_PATH)],
                      files_supporting_client_operation=['leapp-google-sap.repo'],
                      os_version='9', content_channel=ContentChannel.E4S),
    ],
    RHUIFamily(RHUIProvider.ALIBABA, client_files_folder='alibaba'): [
        mk_rhui_setup(clients={'aliyun_rhui_rhel8'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='8'),
        mk_rhui_setup(clients={'aliyun_rhui_rhel9'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='9'),
        mk_rhui_setup(clients={'aliyun_rhui_rhel10'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='10'),
    ],
    RHUIFamily(RHUIProvider.ALIBABA, arch=arch.ARCH_ARM64, client_files_folder='alibaba'): [
        mk_rhui_setup(clients={'aliyun_rhui_rhel8'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='8'),
        mk_rhui_setup(clients={'aliyun_rhui_rhel9'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='9'),
        mk_rhui_setup(clients={'aliyun_rhui_rhel10'}, leapp_pkg='leapp-rhui-alibaba',
                      mandatory_files=[('leapp-alibaba.repo', YUM_REPOS_PATH)],
                      optional_files=[
                        ('key.pem', RHUI_PKI_DIR),
                        ('content.crt', RHUI_PKI_PRODUCT_DIR)
                      ],
                      os_version='10'),
    ]
}


def get_upg_path():
    """
    Get upgrade path in specific string format
    """
    source_major_version = get_source_major_version()
    target_major_version = get_target_major_version()
    return '{0}to{1}'.format(source_major_version, target_major_version)


def get_all_known_rhui_pkgs_for_current_upg():
    upg_major_versions = (get_source_major_version(), get_target_major_version())

    known_pkgs = set()
    for setup_family in RHUI_SETUPS.values():
        for setup in setup_family:
            setup_major = str(setup.os_version[0])
            if setup_major not in upg_major_versions:
                continue
            known_pkgs.update(setup.clients)
            known_pkgs.add(setup.leapp_pkg)

    return known_pkgs
