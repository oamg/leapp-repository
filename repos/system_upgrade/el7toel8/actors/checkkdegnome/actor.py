"""
Actor to check if KDE and/or GNOME are installed
Author: Jan Beran
Email: jaberan@redhat.com
"""

from leapp.actors import Actor
from leapp.reporting import Report
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp.libraries.actor.library import check_kde_gnome
from leapp.models import (InstalledRPM, InstalledDesktopsFacts,
                          InstalledKdeAppsFacts)


class CheckKdeGnome(Actor):
    """
    Checks whether KDE is installed

    Actor will check whether KDE is installed together with GNOME desktop to inform whether we can
    inhibit the upgrade process. When both are installed, we need to inform the user that KDE will
    be removed and GNOME will be used instead. If only KDE is installed, we want to inhibit
    the upgrade process otherwise the user will end up without a desktop.
    """
    name = 'check_kde_gnome'
    consumes = (InstalledRPM, InstalledDesktopsFacts, InstalledKdeAppsFacts)
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_kde_gnome()
