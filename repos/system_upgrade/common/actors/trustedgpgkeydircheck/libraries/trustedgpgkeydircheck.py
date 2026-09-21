import os

from leapp import reporting
from leapp.libraries.common.gpg import (
    get_path_to_gpg_certs,
    GPG_PQC_CERTS_SUBFOLDER,
    is_nogpgcheck_set,
    iter_gpg_keyfiles,
    parse_gpg_key_from_file
)
from leapp.libraries.stdlib import api, format_list


def _report_misplaced_pqc_keys(misplaced_keys, pqc_dir):
    entries = [
        '{keyfile} (PQC key IDs: {key_ids})'.format(keyfile=keyfile, key_ids=', '.join(key_ids))
        for keyfile, key_ids in misplaced_keys
    ]
    summary = (
        'Post-quantum (OpenPGP v6) GPG keys were found directly in the top-level of the'
        ' trusted GPG keys directory. Post-quantum keys must be stored in its'
        ' \'{pqc_subdir}\' subdirectory instead, because not all the tooling used during'
        ' the upgrade can handle key files that contain post-quantum keys, especially key'
        ' files that mix them with non-post-quantum keys. The following key files contain'
        ' the listed post-quantum keys at the top-level of the directory instead of'
        ' the \'{pqc_subdir}\' subdirectory:{key_list}'
        .format(
            pqc_subdir=GPG_PQC_CERTS_SUBFOLDER,
            key_list=format_list(entries, callback_sort=None)
        )
    )
    hint = (
        'Move each listed key file into the \'{pqc_dir}\' directory. If a key file mixes'
        ' post-quantum (v6) and non-post-quantum keys, split it so that the post-quantum'
        ' keys go into a separate file placed in the \'{pqc_dir}\' directory while only'
        ' the non-post-quantum keys remain in the top-level directory.'
        .format(pqc_dir=pqc_dir)
    )
    reporting.create_report([
        reporting.Title('Misplaced post-quantum GPG keys found in the trusted keys directory'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.REPOSITORY, reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint=hint),
    ])


def process():
    """
    Inhibit the upgrade if a v6 (PQC) key is placed at the top-level of the trusted GPG keys dir.

    Note that on source systems older than 9.8, where 'sq' is not available, the
    keys are parsed by gpg2, which reports all of them as v4 keys, so misplaced
    v6 keys cannot be detected there. Such keys are unusable on those systems
    anyway.
    """
    if is_nogpgcheck_set():
        api.current_logger().warning('The --nogpgcheck option is used: skipping the trusted GPG keys directory check.')
        return

    root_dir = get_path_to_gpg_certs()

    misplaced_keys = []
    for keyfile in iter_gpg_keyfiles(root_dir, include_pqc=False):
        pqc_key_ids = [key.short_keyid for key in parse_gpg_key_from_file(keyfile) if key.is_pqc]
        if pqc_key_ids:
            misplaced_keys.append((keyfile, pqc_key_ids))

    if misplaced_keys:
        _report_misplaced_pqc_keys(misplaced_keys, os.path.join(root_dir, GPG_PQC_CERTS_SUBFOLDER))
