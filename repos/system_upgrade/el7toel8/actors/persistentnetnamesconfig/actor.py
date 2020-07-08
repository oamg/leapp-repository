import re

from leapp.actors import Actor
from leapp.libraries.actor.persistentnetnamesconfig import generate_link_file
from leapp.models import PersistentNetNamesFacts, PersistentNetNamesFactsInitramfs
from leapp.models import RenamedInterface, RenamedInterfaces, InitrdIncludes
from leapp.tags import ApplicationsPhaseTag, IPUWorkflowTag


class PersistentNetNamesConfig(Actor):
    """
    Generate udev persistent network naming configuration

    This actor generates systemd-udevd link files for each physical ethernet interface present on RHEL-7
    in case we notice that interace name differs on RHEL-8. Link file configuration will assign RHEL-7 version of
    a name. Actors produces list of interfaces which changed name between RHEL-7 and RHEL-8.
    """

    name = 'persistentnetnamesconfig'
    consumes = (PersistentNetNamesFacts, PersistentNetNamesFactsInitramfs)
    produces = (RenamedInterfaces, InitrdIncludes)
    tags = (ApplicationsPhaseTag, IPUWorkflowTag)
    initrd_files = []

    def process(self):
        rhel7_ifaces = next(self.consume(PersistentNetNamesFacts)).interfaces
        rhel8_ifaces = next(self.consume(PersistentNetNamesFactsInitramfs)).interfaces

        rhel7_ifaces_map = {iface.mac: iface for iface in rhel7_ifaces}
        rhel8_ifaces_map = {iface.mac: iface for iface in rhel8_ifaces}

        renamed_interfaces = []

        if rhel7_ifaces != rhel8_ifaces:
            for iface in rhel7_ifaces:
                rhel7_name = rhel7_ifaces_map[iface.mac].name
                rhel8_name = rhel8_ifaces_map[iface.mac].name

                if rhel7_name != rhel8_name:
                    self.log.warning('Detected interface rename {} -> {}.'.format(rhel7_name, rhel8_name))

                    if re.search('eth[0-9]+', iface.name) is not None:
                        self.log.warning('Interface named using eth prefix, refusing to generate link file')
                        renamed_interfaces.append(RenamedInterface(**{'rhel7_name': rhel7_name,
                                                                      'rhel8_name': rhel8_name}))
                        continue

                    self.initrd_files.append(generate_link_file(iface))

        self.produce(RenamedInterfaces(renamed=renamed_interfaces))
        self.produce(InitrdIncludes(files=self.initrd_files))
