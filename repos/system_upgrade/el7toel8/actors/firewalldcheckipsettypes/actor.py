from leapp.actors import Actor
from leapp.models import Inhibitor
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.actor import private

import os
import xml.etree.ElementTree as ElementTree


class FirewalldCheckIpsetTypes(Actor):
    """
    firewalld's nftables backend does not yet support all ipset types. Support
    is missing in nftables (sets with concatenations and intervals). The
    nftables backend is the preferred backend in RHEL-8 so we must catch
    configurations that use the unsupported ipset types.

    This is expected to be a temporary actor. nftables support for set
    concatenations with intervals is a work in progress.
    """

    name = 'firewalld_check_ipset_types'
    consumes = ()
    produces = (Inhibitor,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process_ipset(self, name, path):
        tree = ElementTree.parse(path)
        root = tree.getroot()

        for ipset in root.iter('ipset'):
            if 'type' in ipset.attrib and \
               not private.isIpsetTypeSupportedByNftables(ipset.attrib['type']):
                self.produce(
                    Inhibitor(
                        summary='Firewalld is using an unsupported ipset type.',
                        details='ipset \'{}\' is of type \'{}\' which is not supported by firewalld\'s nftables backend.'.format(name, ipset.attrib['type']),
                        solutions='Remove ipsets of type {} from firewalld.'.format(ipset.attrib['type'])
                        ))

    def process(self):
        directory = '/etc/firewalld/ipsets'
        for file in os.listdir(directory):
            if not file.endswith('.xml'):
                continue

            self.process_ipset(file[:-4], os.path.join(directory, file))
