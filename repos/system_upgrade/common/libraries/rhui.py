import os

import six

from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api

# when on AWS and upgrading from RHEL 7, we need also Python2 version of "Amazon-id" dnf
# plugin which is served by "leapp-rhui-aws" rpm package (please note this package is not
# in any RH official repository but only in "rhui-client-config-*" repo)
DNF_PLUGIN_PATH_PY2 = '/usr/lib/python2.7/site-packages/dnf-plugins/'
YUM_REPOS_PATH = '/etc/yum.repos.d'

RHUI_PKI_DIR = '/etc/pki/rhui'
RHUI_PKI_PRODUCT_DIR = os.path.join(RHUI_PKI_DIR, 'product')
RHUI_PKI_PRIVATE_DIR = os.path.join(RHUI_PKI_DIR, 'private')

AWS_DNF_PLUGIN_NAME = 'amazon-id.py'


# The files in 'files_map' are provided by special Leapp rpms (per cloud) and
# are delivered into "repos/system_upgrade/common/files/rhui/<PROVIDER>


RHUI_CLOUD_MAP = {
    '7to8': {
        'aws': {
            'src_pkg': 'rh-amazon-rhui-client',
            'target_pkg': 'rh-amazon-rhui-client',
            'leapp_pkg': 'leapp-rhui-aws',
            'leapp_pkg_repo': 'leapp-aws.repo',
            'files_map': [
                ('rhui-client-config-server-8.crt', RHUI_PKI_PRODUCT_DIR),
                ('rhui-client-config-server-8.key', RHUI_PKI_DIR),
                ('content-rhel8.crt', RHUI_PKI_PRODUCT_DIR),
                ('content-rhel8.key', RHUI_PKI_DIR),
                ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                ('leapp-aws.repo', YUM_REPOS_PATH)
            ],
        },
        'aws-sap-e4s': {
            'src_pkg': 'rh-amazon-rhui-client-sap-bundle',
            'target_pkg': 'rh-amazon-rhui-client-sap-bundle-e4s',
            'leapp_pkg': 'leapp-rhui-aws-sap-e4s',
            'leapp_pkg_repo': 'leapp-aws-sap-e4s.repo',
            'files_map': [
                ('rhui-client-config-server-8-sap-bundle.crt', RHUI_PKI_PRODUCT_DIR),
                ('rhui-client-config-server-8-sap-bundle.key', RHUI_PKI_DIR),
                ('content-rhel8-sap.crt', RHUI_PKI_PRODUCT_DIR),
                ('content-rhel8-sap.key', RHUI_PKI_DIR),
                ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                (AWS_DNF_PLUGIN_NAME, DNF_PLUGIN_PATH_PY2),
                ('leapp-aws-sap-e4s.repo', YUM_REPOS_PATH)
            ],
        },
        'azure': {
            'src_pkg': 'rhui-azure-rhel7',
            'target_pkg': 'rhui-azure-rhel8',
            'agent_pkg': 'WALinuxAgent',
            'leapp_pkg': 'leapp-rhui-azure',
            'leapp_pkg_repo': 'leapp-azure.repo',
            'files_map': [
                ('content.crt', RHUI_PKI_PRODUCT_DIR),
                ('key.pem', RHUI_PKI_PRIVATE_DIR),
                ('leapp-azure.repo', YUM_REPOS_PATH)
            ],
        },
        'azure-sap': {
            'src_pkg': 'rhui-azure-rhel7-base-sap-ha',
            'target_pkg': 'rhui-azure-rhel8-sap-ha',
            'agent_pkg': 'WALinuxAgent',
            'leapp_pkg': 'leapp-rhui-azure-sap',
            'leapp_pkg_repo': 'leapp-azure-sap.repo',
            'files_map': [
                ('content-rhel8-sap-ha.crt', RHUI_PKI_PRODUCT_DIR),
                ('key-rhel8-sap-ha.pem', RHUI_PKI_DIR),
                ('leapp-azure-sap.repo', YUM_REPOS_PATH)
            ],
        },
    },
    '8to9': {
        'aws': {
            'src_pkg': 'rh-amazon-rhui-client-ha',
            'target_pkg': 'rh-amazon-rhui-client',
            'leapp_pkg': 'leapp-rhui-aws',
            'leapp_pkg_repo': 'leapp-aws.repo',
            'files_map': [
                ('rhui-client-config-server-9.crt', RHUI_PKI_PRODUCT_DIR),
                ('rhui-client-config-server-9.key', RHUI_PKI_DIR),
                ('content-rhel9.crt', RHUI_PKI_PRODUCT_DIR),
                ('content-rhel9.key', RHUI_PKI_DIR),
                ('cdn.redhat.com-chain.crt', RHUI_PKI_DIR),
                ('leapp-aws.repo', YUM_REPOS_PATH)
            ],
        },
    },
}


def get_upg_path():
    """
    Get upgrade path in specific string format
    """
    return '7to8' if get_target_major_version() == '8' else '8to9'


def gen_rhui_files_map():
    """
    Generate RHUI files map based on architecture and upgrade path
    """
    arch = api.current_actor().configuration.architecture
    upg_path = get_upg_path()

    cloud_map = RHUI_CLOUD_MAP
    # for the moment the only arch related difference in RHUI package naming is on ARM
    if arch == 'aarch64':
        cloud_map[get_upg_path()]['aws']['src_pkg'] = 'rh-amazon-rhui-client-arm'

    files_map = dict((k, v['files_map']) for k, v in six.iteritems(cloud_map[upg_path]))
    return files_map


def copy_rhui_data(context, provider):
    """
    Copy relevant RHUI cerificates and key into the target userspace container
    """
    rhui_dir = api.get_common_folder_path('rhui')
    data_dir = os.path.join(rhui_dir, provider)

    context.call(['mkdir', '-p', RHUI_PKI_PRODUCT_DIR])
    context.call(['mkdir', '-p', RHUI_PKI_PRIVATE_DIR])

    for path_ in gen_rhui_files_map().get(provider, ()):
        context.copy_to(os.path.join(data_dir, path_[0]), path_[1])
