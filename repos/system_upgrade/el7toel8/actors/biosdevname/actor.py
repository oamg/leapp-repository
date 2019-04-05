import pyudev
import re

from leapp.actors import Actor
from leapp.models import PersistentNetNamesFacts, KernelCmdlineArg
from leapp.tags import FactsPhaseTag, IPUWorkflowTag
from leapp.libraries.stdlib import run, CalledProcessError
from leapp.exceptions import StopActorExecutionError


class Biosdevname(Actor):
    """
    Enable biosdevname on RHEL8 if all interfaces on RHEL-7 used biosdevname naming scheme or if machine vendor is DELL
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
        dmi = pyudev.Enumerator(context).match_subsystem('dmi')
        dev = list(filter(lambda d: d.sys_name == 'id', dmi))[0]
        vendor = dev.attributes.get('sys_vendor')

        return re.search('Dell.*', str(vendor)) is not None

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
