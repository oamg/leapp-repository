import os
from collections import defaultdict

from leapp import reporting
from leapp.libraries.common.gpg import get_path_to_gpg_certs, GPG_PQC_CERTS_SUBFOLDER, is_nogpgcheck_set
from leapp.libraries.stdlib import api, format_list
from leapp.models import MisplacedTrustedGpgKeys


def _format_section(header, misplaced_keys):
    entries = [
        f'{os.path.basename(keyfile)} (key IDs: {", ".join(key_ids)})'
        for keyfile, key_ids in misplaced_keys.items()
    ]
    return f'\n{header}{format_list(entries)}'


def _report_misplaced_keys(misplaced_pqc_keys, misplaced_non_pqc_keys, root_dir, pqc_dir):
    summary = (
        f"Found GPG keys in an incorrect location under the trusted RPM GPG keys directory '{root_dir}'."
        'Keys need to be placed in the appropriate directory depending on their type:\n'
        f'  - Post-quantum (OpenPGP v6) keys: {pqc_dir}/\n'
        f'  - Standard (non-PQC) keys:        {root_dir}/\n'
        'This separation is required because some of the tooling used during the'
        ' upgrade cannot process post-quantum keys, especially if they are mixed with standard keys within'
        ' a single keyfile.\n'
        'Misplaced keys found:'
    )
    if misplaced_pqc_keys:
        header = (
            f"Post-quantum keys found in {root_dir} instead of the '{GPG_PQC_CERTS_SUBFOLDER}' subdirectory:"
        )
        summary += _format_section(header, misplaced_pqc_keys)
    if misplaced_non_pqc_keys:
        header = (
            f"Standard keys found in the '{GPG_PQC_CERTS_SUBFOLDER}' subdirectory instead of {root_dir}:"
        )
        summary += _format_section(header, misplaced_non_pqc_keys)

    hint = (
        "Move each misplaced key file to its appropriate location. "
        "If a key file contains both key types, split it into separate files "
        "by type and place them in the locations described above.\n"
        "The 'sq packet dump' command can be used to inspect versions of keys in a file."
    )
    reporting.create_report([
        reporting.Title('Misplaced GPG keys found in the trusted keys directory'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.REPOSITORY, reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint=hint),
    ])


def process():
    """
    Inhibit the upgrade if misplaced GPG keys are found

    The 'pqc' subdirectory must contain post-quantum (v6) keys only and the
    top-level of the directory all other (non-post-quantum) keys. The upgrade is
    inhibited if a post-quantum key is found at the top-level or a non-post-quantum
    key is found in the 'pqc' subdirectory.

    Note that on source systems older than 9.9, where 'sq' is not available, the
    keys are parsed by gpg2 instead which can't read v6 keys at all. Therefore,
    misplaced v6 keys at the top-level cannot be detected there.
    """
    if is_nogpgcheck_set():
        api.current_logger().debug(
            "The --nogpgcheck option is used: skipping the trusted GPG keys directory check."
        )
        return

    misplaced_msg = next(api.consume(MisplacedTrustedGpgKeys), None)
    if not misplaced_msg:
        api.current_logger().debug('No MisplacedTrustedGpgKeys received, skipping execution.')
        return

    misplaced_pqc = misplaced_msg.pqc_keys
    misplaced_classic = misplaced_msg.classic_keys
    if not misplaced_pqc and not misplaced_classic:
        api.current_logger().debug('No misplaced keys detected, skipping execution.')
        return

    def map_by_keyfile(keys):
        by_keyfile = defaultdict(list)
        for key in keys:
            by_keyfile[key.filename].append(key.fingerprint)
        return by_keyfile

    misplaced_pqc = map_by_keyfile(misplaced_pqc)
    misplaced_classic = map_by_keyfile(misplaced_classic)

    root_dir = get_path_to_gpg_certs()
    pqc_dir = os.path.join(root_dir, GPG_PQC_CERTS_SUBFOLDER)
    _report_misplaced_keys(misplaced_pqc, misplaced_classic, root_dir, pqc_dir)
