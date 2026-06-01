from leapp.actors import Actor
from leapp.libraries.actor import checkvarrunsymlink
from leapp.models import TrackedFilesInfoSource
from leapp.reporting import Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class CheckVarRunSymlink(Actor):
    """
    Check that /var/run is a symlink pointing to /run.

    In modern Linux systems that use systemd, /run is a tmpfs filesystem
    managed by systemd and /var/run must be a symbolic link pointing to
    ../run for compatibility. Inhibit the upgrade if /var/run is not
    configured as expected, as this can cause boot failures, service
    startup failures, or login issues.
    """

    name = 'check_var_run_symlink'
    consumes = (TrackedFilesInfoSource,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        checkvarrunsymlink.process()
