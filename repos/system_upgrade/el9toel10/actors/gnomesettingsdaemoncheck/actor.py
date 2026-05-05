from leapp.actors import Actor
from leapp.libraries.actor import gnomesettingsdaemoncheck
from leapp.models import RpmTransactionTasks
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class GnomeSettingsDaemonCheck(Actor):
    """
    Install gnome-settings-daemon-server-defaults on graphical server upgrades.

    If the graphical-server-environment comps environment group was installed on
    the source RHEL 9 system, schedules the installation of the
    gnome-settings-daemon-server-defaults package during the upgrade to RHEL 10.
    """

    name = 'gnome_settings_daemon_check'
    consumes = ()
    produces = (RpmTransactionTasks,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        gnomesettingsdaemoncheck.process()
