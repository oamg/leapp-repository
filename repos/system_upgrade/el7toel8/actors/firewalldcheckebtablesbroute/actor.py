from leapp.actors import Actor
from leapp.models import Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.actor import private

import os
import xml.etree.ElementTree as ElementTree


class FirewalldCheckEbtablesBroute(Actor):
    """
    In RHEL-8 the ebtables table broute is not available. If the user is using
    firewalld direct rules that utilize this table then we need to inhibit the
    upgrade.
    """

    name = 'firewalld_check_ebtables_broute'
    consumes = ()
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self):
        path = '/etc/firewalld/direct.xml'
        if not os.path.exists(path):
            return

        tree = ElementTree.parse(path)
        root = tree.getroot()

        if private.isEbtablesBrouteTableInUse(root):
            self.produce(
                Inhibitor(
                    summary='Firewalld is using ebtables broute table.',
                    details='ebtables in RHEL-8 does not support the broute table.',
                    solutions='Remove firewalld direct rules that use ebtables broute table.'
                    ))
