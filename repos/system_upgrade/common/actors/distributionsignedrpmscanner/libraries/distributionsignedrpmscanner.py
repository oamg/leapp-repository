from leapp.libraries.common import rhui
from leapp.libraries.common.config import get_env
from leapp.libraries.common.distro import get_distribution_data
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM, InstalledRedHatSignedRPM, InstalledRPM, InstalledUnsignedRPM


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


def process():
    distribution = api.current_actor().configuration.os_release.release_id
    distro_keys = get_distribution_data(distribution).get('keys', [])
    all_signed = get_env('LEAPP_DEVEL_RPMS_ALL_SIGNED', '0') == '1'
    rhui_pkgs = rhui.get_all_known_rhui_pkgs_for_current_upg()

    signed_pkgs = DistributionSignedRPM()
    rh_signed_pkgs = InstalledRedHatSignedRPM()
    unsigned_pkgs = InstalledUnsignedRPM()

    for rpm_pkgs in api.consume(InstalledRPM):
        for pkg in rpm_pkgs.items:
            if all_signed or is_distro_signed(pkg, distro_keys) or is_exceptional(pkg, rhui_pkgs):
                signed_pkgs.items.append(pkg)
                if distribution == 'rhel':
                    rh_signed_pkgs.items.append(pkg)
                continue
            unsigned_pkgs.items.append(pkg)

    api.produce(signed_pkgs)
    api.produce(rh_signed_pkgs)
    api.produce(unsigned_pkgs)
