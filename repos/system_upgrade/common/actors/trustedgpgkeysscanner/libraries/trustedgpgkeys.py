from leapp.exceptions import StopActorExecutionError
from leapp.libraries.common.gpg import get_gpg_fp_from_file, get_pubkeys_from_rpms, iter_gpg_keyfiles
from leapp.libraries.stdlib import api
from leapp.models import GpgKey, InstalledRPM, TrustedGpgKeys


def _get_pubkeys(installed_rpms):
    """
    Get pubkeys from installed rpms and the trusted directory
    """
    pubkeys = get_pubkeys_from_rpms(installed_rpms)
    db_pubkeys = [key.fingerprint for key in pubkeys]

    for key_file in iter_gpg_keyfiles(include_pqc=True):
        fps = get_gpg_fp_from_file(key_file)
        for fp in fps:
            if fp not in db_pubkeys:
                pubkeys.append(GpgKey(fingerprint=fp, rpmdb=False, filename=key_file))
                db_pubkeys += fp
    return pubkeys


def process():
    """
    Process keys in RPM DB and the ones in trusted directory to produce a list of trusted keys
    """

    try:
        installed_rpms = next(api.consume(InstalledRPM))
    except StopIteration:
        raise StopActorExecutionError(
            'Could not check for valid GPG keys', details={'details': 'No InstalledRPM facts'}
        )
    pubkeys = _get_pubkeys(installed_rpms)
    api.produce(TrustedGpgKeys(items=pubkeys))
