"""
Top-level orchestration for the ``targetuserspacecreator`` actor.

:func:`perform` is the actor's single entry point and the only producer of messages. It runs the build steps in
order and produces the three output messages together, only after a successful build. Any hard stop raised earlier
(input validation, missing certificate, repository inhibitors, RHUI/dnf failures) results in no output messages.

This is the high-layer module of the actor; it imports every other ``tus_*`` module.
"""

from leapp import reporting
from leapp.libraries.actor import tus_contentaccess, tus_inputdata, tus_layout, tus_targetrepos, tus_userspacebuild
from leapp.libraries.common import rhsm
from leapp.libraries.common.config import get_product_type
from leapp.libraries.stdlib import api


def _report_missing_target_cert():
    """
    Report a high-severity inhibitor about a missing target product certificate.

    Translates a missing target product certificate into a user-facing inhibitor report. When the target product
    type is beta, a beta-specific note is appended to the summary. The report includes remediation advice to set the
    target release explicitly via ``LEAPP_DEVEL_TARGET_RELEASE`` / ``--target-version``. This only creates a report;
    it does not stop execution or produce any output message by itself.
    """
    summary = (
        'Cannot find a product certificate for the target system. This is'
        ' required to access the target content via subscription-manager.'
    )
    if get_product_type('target') == 'beta':
        summary += (
            ' Note that a Beta target requires a Beta product certificate; make'
            ' sure the target release you selected is available as Beta.'
        )
    reporting.create_report([
        reporting.Title('Missing target system product certificate'),
        reporting.Summary(summary),
        reporting.Severity(reporting.Severity.HIGH),
        reporting.Groups([reporting.Groups.SANITY]),
        reporting.Groups([reporting.Groups.INHIBITOR]),
        reporting.Remediation(hint=(
            'If the target version is not released yet, set the target release'
            ' explicitly via LEAPP_DEVEL_TARGET_RELEASE / --target-version.'
        )),
    ])


def perform():
    """
    Run the actor's build steps and produce the output messages.

    Gathers and validates inputs, resolves the on-disk layout, and then, within a scratch container (overlay plus
    systemd-nspawn and an optional installation ISO), establishes content access, selects the target repositories,
    builds the target userspace, and parses the resulting repository snapshot. On success, the target userspace
    info, the used target repositories, and the repository snapshot are produced together as output messages.

    If a target product certificate is missing, a corresponding inhibitor is reported and the function returns
    without producing any output message.

    .. seealso::
        :func:`leapp.libraries.actor.tus_inputdata.gather` for input-validation hard stops.

        :func:`leapp.libraries.actor.tus_layout.scratch_container` for scratch container setup failures.

        :func:`leapp.libraries.actor.tus_contentaccess.establish` for content access (RHUI/RHSM/dnf) failures.

        :func:`leapp.libraries.actor.tus_targetrepos.select_target_repositories` for repository inhibitors.

        :func:`leapp.libraries.actor.tus_userspacebuild.build` for userspace build failures.
    """
    # Step 1: consume + validate inputs (hard-stops #1-#3).
    inputs = tus_inputdata.gather()

    # Step 5 (paths): resolve the on-disk layout and overlay free-space reserve.
    layout = tus_layout.compute()

    try:
        # Step 2: establish the scratch container (overlay + nspawn + optional ISO).
        with tus_layout.scratch_container(layout, inputs) as scratch:
            # Step 3: establish content access (RHUI → RHSM → $stream → custom).
            tus_contentaccess.establish(scratch, inputs)

            # Step 4: discover + select target repositories (inhibitors #2-#5).
            used_repos = tus_targetrepos.select_target_repositories(scratch, inputs)

            # Step 5: build the target userspace.
            userspace_info = tus_userspacebuild.build(scratch, layout, inputs, used_repos)

            # Step 6: parse the build (scratch) container's repofiles for the snapshot.
            snapshot = tus_targetrepos.build_target_repositories_snapshot(scratch)
    except rhsm.MissingTargetProductCertificate:
        # Inhibitor #1: report + soft stop, no output messages.
        _report_missing_target_cert()
        return

    # Emit all three messages atomically, only on a successful build.
    api.produce(userspace_info, used_repos, snapshot)
