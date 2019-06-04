import re

import pyudev

from leapp.actors import Actor
from leapp.models import PersistentNetNamesFacts, KernelCmdlineArg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class Biosdevname(Actor):
    """
    Enable biosdevname on RHEL8 if all interfaces on RHEL7 use biosdevname naming scheme and if machine vendor is DELL
    """

    name = 'biosdevname'
    consumes = (PersistentNetNamesFacts,)
    produces = (KernelCmdlineArg,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def is_biosdevname_disabled(self):
        with open('/proc/cmdline') as cmdline:
            if 'biosdevname=0' in cmdline.read():
                return True

        return False

    def is_vendor_dell(self):
        context = pyudev.Context()

        # There should be only one dmi/id device
        for dev in pyudev.Enumerator(context).match_subsystem('dmi').match_sys_name('id'):
            vendor = dev.attributes.get('sys_vendor')
            return re.search('Dell.*', str(vendor)) is not None
        return False

    def all_interfaces_biosdevname(self, interfaces):
        # Biosdevname supports two naming schemes
        emx = re.compile('em[0-9]+')
        pxpy = re.compile('p[0-9]+p[0-9]+')

        for i in interfaces:
            if emx.match(i.name) is None and pxpy.match(i.name) is None:
                return False

        return True

    def enable_biosdevname(self):
        self.log.info("Biosdevname naming scheme in use, explicitely enabling biosdevname on RHEL-8")
        self.produce(KernelCmdlineArg(**{'key': 'biosdevname', 'value': '1'}))

    def process(self):
        interfaces = next(self.consume(PersistentNetNamesFacts)).interfaces

        if self.is_biosdevname_disabled():
            return

        if self.is_vendor_dell() and self.all_interfaces_biosdevname(interfaces):
            self.enable_biosdevname()
