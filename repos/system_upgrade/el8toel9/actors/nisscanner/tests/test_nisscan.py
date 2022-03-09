import mock
import pytest
import six

from leapp.libraries.actor import nisscan
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import NISConfig

# Examples of /etc/yp.conf configuration file (default and configured)
YPBIND_DEFAULT_CONF = """# /etc/yp.conf - ypbind configuration file
# Valid entries are
#
# domain NISDOMAIN server HOSTNAME
#	Use server HOSTNAME for the domain NISDOMAIN"""

YPBIND_CONFIGURED_CONF = """# /etc/yp.conf - ypbind configuration file
domain whoisredhat.redhat server prod-db

domain whatisredhat.redhat server prod-db"""


@pytest.mark.parametrize('pkgs_installed', [
    ('ypserv',),
    ('ypbind',),
    ('ypserv-not-ypbind',),
    ('ypbind', 'ypserv'),
])
@pytest.mark.parametrize("fill_conf_file", [True, False])
@pytest.mark.parametrize("fill_ypserv_dir", [True, False])
def test_actor_nisscan(monkeypatch, pkgs_installed, fill_conf_file, fill_ypserv_dir):
    """
    Parametrized helper function for test_actor_* functions.

    Run the actor feeded with our mocked functions and assert
    produced messages according to set arguments.

    Parameters:
        pkgs_installed  (touple): installed pkgs
        fill_conf_file  (bool): not default ypbind config file
        fill_ypserv_dir  (bool): not default ypserv dir content
    """

    # Store final list of configured NIS packages
    configured_pkgs = []

    # Fill ypbind config
    yp_conf_content = YPBIND_CONFIGURED_CONF if fill_conf_file else YPBIND_DEFAULT_CONF

    # Fill ypserv dir files
    yp_dir_content = (nisscan.YPSERV_DEFAULT_FILES + ('example.com',) if fill_ypserv_dir
                      else nisscan.YPSERV_DEFAULT_FILES)

    # Mock 'isfile' & 'isdir' based on installed pkgs
    mocked_isfile = 'ypbind' in pkgs_installed
    mocked_isdir = 'ypserv' in pkgs_installed

    mock_config = mock.mock_open(read_data=yp_conf_content)
    with mock.patch("builtins.open" if six.PY3 else "__builtin__.open", mock_config):
        curr_actor_mocked = CurrentActorMocked()
        monkeypatch.setattr(api, 'current_actor', curr_actor_mocked)
        monkeypatch.setattr(api, "produce", produce_mocked())
        monkeypatch.setattr(nisscan.os, 'listdir', lambda dummy: yp_dir_content)
        monkeypatch.setattr(nisscan.os.path, 'isfile', lambda dummy: mocked_isfile)
        monkeypatch.setattr(nisscan.os.path, 'isdir', lambda dummy: mocked_isdir)

        # Executed actor feeded with mocked functions
        nisscan.NISScanLibrary().process()

    # Filter NIS pkgs
    filtered_installed_pkgs = [x for x in pkgs_installed if x in nisscan.PACKAGES_NAMES]

    # Create correct list of pkgs for assert check
    for pkg in filtered_installed_pkgs:
        if (pkg == 'ypserv' and fill_ypserv_dir) or (pkg == 'ypbind' and fill_conf_file):
            configured_pkgs.append(pkg)

    # Sort NISConfig objects
    nisconf_template = set(NISConfig(nis_not_default_conf=configured_pkgs).nis_not_default_conf)
    nisconf_result = set(api.produce.model_instances[0].nis_not_default_conf)

    assert nisconf_template == nisconf_result
