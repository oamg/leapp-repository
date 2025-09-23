from leapp.libraries.common import rhui
from leapp.libraries.common.config import get_env, get_source_distro_id
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, InstalledRPM, InstalledUnsignedRPM, ThirdPartyRPM
from leapp.utils.deprecation import suppress_deprecation


def is_distro_signed(pkg, distro_keys):
    return any(key in pkg.pgpsig for key in distro_keys)


def is_exceptional(pkg, allowlist):
    """
    Some packages should be marked always as signed

    tl;dr; gpg-pubkey, katello packages, and rhui packages

    gpg-pubkey is not real RPM. It's just an entry representing
    gpg key imported inside the RPM DB. For that same reason, it cannot be
    signed. Note that it cannot affect the upgrade transaction, so ignore
    who vendored the key. Total majority of all machines have imported third
    party gpg keys.

    Katello packages have various names and are created on a Satellite server.

    The allowlist is now used for any other package names that should be marked
    always as signed for the particular upgrade.
    """
    return pkg.name == 'gpg-pubkey' or pkg.name.startswith('katello-ca-consumer') or pkg.name in allowlist


@suppress_deprecation(InstalledUnsignedRPM)
def process():
    distro = get_source_distro_id()
    distro_keys = get_distribution_data(distro).get('keys', [])
    all_signed = get_env('LEAPP_DEVEL_RPMS_ALL_SIGNED', '0') == '1'
    rhui_pkgs = rhui.get_all_known_rhui_pkgs_for_current_upg()

    signed_pkgs = DistributionSignedRPM()
    unsigned_pkgs = InstalledUnsignedRPM()
    thirdparty_pkgs = ThirdPartyRPM()

    for rpm_pkgs in api.consume(InstalledRPM):
        for pkg in rpm_pkgs.items:
            if all_signed or is_distro_signed(pkg, distro_keys) or is_exceptional(pkg, rhui_pkgs):
                signed_pkgs.items.append(pkg)
            else:
                unsigned_pkgs.items.append(pkg)
                thirdparty_pkgs.items.append(pkg)

    api.produce(signed_pkgs)
    api.produce(unsigned_pkgs)
    api.produce(thirdparty_pkgs)
