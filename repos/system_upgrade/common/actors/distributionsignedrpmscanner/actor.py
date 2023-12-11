import json
import os

from leapp.actors import Actor
from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common import rhui
from leapp.libraries.common.config import get_env
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, InstalledRedHatSignedRPM, InstalledRPM, InstalledUnsignedRPM
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.utils.deprecation import suppress_deprecation


@suppress_deprecation(InstalledRedHatSignedRPM)
class DistributionSignedRpmScanner(Actor):
    """Provide data about installed RPM Packages signed by the distribution.

    After filtering the list of installed RPM packages by signature, a message
    with relevant data will be produced.
    """

    name = 'distribution_signed_rpm_scanner'
    consumes = (InstalledRPM,)
    produces = (DistributionSignedRPM, InstalledRedHatSignedRPM, InstalledUnsignedRPM,)
    tags = (IPUWorkflowTag, FactsPhaseTag)

    def process(self):
        # TODO(pstodulk): refactor this function
        # - move it to the private library
        # - split it into several functions (so the main function stays small)
        # FIXME(pstodulk): gpg-pubkey is handled wrong; it's not a real package
        # and create FP report about unsigned RPMs. Keeping the fix for later.
        distribution = self.configuration.os_release.release_id
        distributions_path = api.get_common_folder_path('distro')

        distribution_config = os.path.join(distributions_path, distribution, 'gpg-signatures.json')
        if os.path.exists(distribution_config):
            with open(distribution_config) as distro_config_file:
                distro_config_json = json.load(distro_config_file)
                distribution_keys = distro_config_json.get('keys', [])
                distribution_packager = distro_config_json.get('packager', 'not-available')
        else:
            raise StopActorExecutionError(
                'Cannot find distribution signature configuration.',
                details={'Problem': 'Distribution {} was not found in {}.'.format(distribution, distributions_path)})

        signed_pkgs = DistributionSignedRPM()
        rh_signed_pkgs = InstalledRedHatSignedRPM()
        unsigned_pkgs = InstalledUnsignedRPM()

        all_signed = get_env('LEAPP_DEVEL_RPMS_ALL_SIGNED', '0') == '1'

        def has_distributionsig(pkg):
            return any(key in pkg.pgpsig for key in distribution_keys)

        def is_gpg_pubkey(pkg):
            """
            Check if gpg-pubkey pkg exists or LEAPP_DEVEL_RPMS_ALL_SIGNED=1

            gpg-pubkey is not signed as it would require another package
            to verify its signature
            """
            return (    # pylint: disable-msg=consider-using-ternary
                    pkg.name == 'gpg-pubkey'
                    and pkg.packager.startswith(distribution_packager)
                    or all_signed
            )

        def has_katello_prefix(pkg):
            """Whitelist the katello package."""
            return pkg.name.startswith('katello-ca-consumer')

        whitelisted_cloud_pkgs = rhui.get_all_known_rhui_pkgs_for_current_upg()

        for rpm_pkgs in self.consume(InstalledRPM):
            for pkg in rpm_pkgs.items:
                if any(
                    [
                        has_distributionsig(pkg),
                        is_gpg_pubkey(pkg),
                        has_katello_prefix(pkg),
                        pkg.name in whitelisted_cloud_pkgs,
                    ]
                ):
                    signed_pkgs.items.append(pkg)
                    if distribution == 'rhel':
                        rh_signed_pkgs.items.append(pkg)
                    continue

                unsigned_pkgs.items.append(pkg)

        self.produce(signed_pkgs)
        self.produce(rh_signed_pkgs)
        self.produce(unsigned_pkgs)
