import re

import pyudev

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.stdlib import api
from leapp.models import KernelCmdlineArg, PersistentNetNamesFacts


def is_biosdevname_disabled():
    with open('/proc/cmdline') as cmdline:
        if 'biosdevname=0' in cmdline.read():
            return True

    return False


def is_vendor_dell():
    context = pyudev.Context()

    # There should be only one dmi/id device
    for dev in pyudev.Enumerator(context).match_subsystem('dmi').match_sys_name('id'):
        vendor = dev.attributes.get('sys_vendor')
        return re.search('Dell.*', str(vendor)) is not None
    return False


def all_interfaces_biosdevname(interfaces):
    # Biosdevname supports two naming schemes
    emx = re.compile('em[0-9]+')
    pxpy = re.compile('p[0-9]+p[0-9]+')

    for i in interfaces:
        if emx.match(i.name) is None and pxpy.match(i.name) is None:
            return False
    return True


def enable_biosdevname():
    api.current_logger().info(
        "Biosdevname naming scheme in use, explicitly enabling biosdevname on the target RHEL system"
    )
    api.produce(KernelCmdlineArg(**{'key': 'biosdevname', 'value': '1'}))


def check_biosdevname():
    if is_biosdevname_disabled():
        return

    net_names_facts_messages = api.consume(PersistentNetNamesFacts)
    net_names_facts = next(net_names_facts_messages, None)
    if not net_names_facts:
        raise StopActorExecutionError(
            'Could not read interfaces names',
            details={'details': 'No PersistentNetNamesFacts message found.'},
        )

    if is_vendor_dell() and all_interfaces_biosdevname(net_names_facts.interfaces):
        enable_biosdevname()
