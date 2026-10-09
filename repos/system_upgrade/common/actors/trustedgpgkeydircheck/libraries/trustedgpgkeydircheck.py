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


def _format_section(header, misplaced_keys):
    entries = [
        '{keyfile} (key IDs: {key_ids})'.format(keyfile=keyfile, key_ids=', '.join(key_ids))
        for keyfile, key_ids in misplaced_keys
    ]
    return '\n{header}{key_list}'.format(header=header, key_list=format_list(entries))


def _report_misplaced_keys(misplaced_pqc_keys, misplaced_non_pqc_keys, root_dir, pqc_dir):
    summary = (
        'Trusted GPG keys are stored in a wrong location. Post-quantum (OpenPGP v6) keys must'
        ' be stored in the \'{pqc_subdir}\' subdirectory of the trusted GPG keys directory,'
        ' while all other (non-post-quantum) keys must be stored in the top-level of the'
        ' directory. This split is required because not all the tooling used during the'
        ' upgrade can handle key files that contain post-quantum keys, especially key files'
        ' that mix them with non-post-quantum keys. The following misplaced keys were found:'
        .format(pqc_subdir=GPG_PQC_CERTS_SUBFOLDER)
    )
    if misplaced_pqc_keys:
        header = (
            'Post-quantum keys at the top-level instead of the \'{pqc_subdir}\' subdirectory:'
            .format(pqc_subdir=GPG_PQC_CERTS_SUBFOLDER)
        )
        summary += _format_section(header, misplaced_pqc_keys)
    if misplaced_non_pqc_keys:
        header = (
            'Non-post-quantum keys in the \'{pqc_subdir}\' subdirectory instead of the top-level:'
            .format(pqc_subdir=GPG_PQC_CERTS_SUBFOLDER)
        )
        summary += _format_section(header, misplaced_non_pqc_keys)

    hint = (
        'Move each misplaced key file to the correct location: post-quantum keys into the'
        ' \'{pqc_dir}\' directory and all other keys into the top-level \'{root_dir}\''
        ' directory. If a key file mixes post-quantum and non-post-quantum keys, split it so'
        ' that the post-quantum keys go into a file in the \'{pqc_dir}\' directory while the'
        ' non-post-quantum keys go into a file in the top-level directory.'
        .format(pqc_dir=pqc_dir, root_dir=root_dir)
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
    Inhibit the upgrade if the trusted GPG keys directory layout is wrong.

    The 'pqc' subdirectory must contain post-quantum (v6) keys only and the
    top-level of the directory all other (non-post-quantum) keys. The upgrade is
    inhibited if a post-quantum key is found at the top-level or a non-post-quantum
    key is found in the 'pqc' subdirectory.

    Note that on source systems older than 9.9, where 'sq' is not available, the
    keys are parsed by gpg2 instead which can't read v6 keys at all. Therefore,
    misplaced v6 keys at the top-level cannot be detected there.
    """
    if is_nogpgcheck_set():
        api.current_logger().warning('The --nogpgcheck option is used: skipping the trusted GPG keys directory check.')
        return

    root_dir = get_path_to_gpg_certs()
    pqc_dir = os.path.join(root_dir, GPG_PQC_CERTS_SUBFOLDER)

    misplaced_pqc_keys = []  # post-quantum (v6) keys found at the top-level
    misplaced_non_pqc_keys = []  # non-post-quantum keys found in the 'pqc' subdirectory
    for keyfile in iter_gpg_keyfiles(root_dir, include_pqc=True):
        keys = parse_gpg_key_from_file(keyfile)
        if os.path.dirname(keyfile) == pqc_dir:
            non_pqc_key_ids = [key.short_keyid for key in keys if not key.is_pqc]
            if non_pqc_key_ids:
                misplaced_non_pqc_keys.append((keyfile, non_pqc_key_ids))
        else:  # subdirs other than pqc are ignored by the iterator
            pqc_key_ids = [key.short_keyid for key in keys if key.is_pqc]
            if pqc_key_ids:
                misplaced_pqc_keys.append((keyfile, pqc_key_ids))

    if misplaced_pqc_keys or misplaced_non_pqc_keys:
        _report_misplaced_keys(misplaced_pqc_keys, misplaced_non_pqc_keys, root_dir, pqc_dir)
