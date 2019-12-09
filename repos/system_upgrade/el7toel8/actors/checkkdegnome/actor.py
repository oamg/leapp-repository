"""
Actor to check if KDE and/or GNOME are installed
Author: Jan Beran
Email: jaberan@redhat.com
"""

from leapp.actors import Actor
from leapp.tags import IPUWorkflowTag, ChecksPhaseTag
from leapp.reporting import Report
from leapp.libraries.actor.library import check_kde_gnome


class CheckKdeGnome(Actor):
    """
    Checks whether KDE is installed

    Actor will check whether KDE is installed together with GNOME desktop to inform whether we can
    inhibit the upgrade process. When both are installed, we need to inform the user that KDE will
    be removed and GNOME will be used instead. If only KDE is installed, we want to inhibit
    the upgrade process otherwise the user will end up without a desktop.
    Also if both are installed, but KDE is not used as default desktop, we further check most common
    KDE apps to inform the user that those will be removed in case the user is using them.
    """
    name = 'check_kde_gnome'
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)

    def process(self):
        check_kde_gnome()
