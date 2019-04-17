from leapp.actors import Actor
from leapp.reporting import Report
from leapp.libraries.common.reporting import report_generic
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag
from leapp.libraries.common.reporting import report_with_remediation
import ipaddress
import re

def get_line(it):
    line = next(it)

    if line.endswith("\\\n"):
        line = line[:-2] + " " + get_line(it)

    return line

class CheckNis(Actor):
    """
    Check configuration of ypbind and nsswitch. Address of NIS server cannot be
    specified by host name if NIS is used to resolve host names.
    """

    name = "check_nis_nsswitch"
    consumes = ()
    produces = (Report,)
    tags = (IPUWorkflowTag, ChecksPhaseTag)


    def nis_in_nsswitch_hosts(self):
        """
        Check if hosts are resolved by NIS (nsswitch.conf)
        """

        try:
            fp = open("/etc/nsswitch.conf")
            rawlines = fp.readlines()
            fp.close()
        except:
            return False

        #remove comments
        rawlines = list(map(lambda x: x.split("#",1)[0], rawlines))


        iter_rawlines = iter(rawlines)
        lines = list()
        while True:
            try:
                lines.append(get_line(iter_rawlines))
            except StopIteration:
                break

        # replace newlines by spaces
        lines = list(map(lambda x: x.replace("\n", " "), lines))

        # filter hosts entries
        lines  = list(filter(lambda x: re.match("^\s*hosts\s*:",x) is not None,\
                lines))

        for l in lines:
            sources = l.split(":", 1)[1]

            if "nis" in sources.split(" "):
                return True

        return False

    def hostnames_in_yp_conf(self):

        try:
            fp = open("/etc/yp.conf")
            lines = fp.readlines()
            fp.close()
        except:
            return []

        #remove comments
        lines = list(map(lambda x: x.split("#",1)[0], lines))

        re_server = r"\s*domain\s+\S+\s+server\s+(\S+)\s*"
        re_ypserver = r"\s*ypserver\s+(\S+)\s*"

        # Find server name specified in form: domain NISDOMAIN server HOSTNAME
        mtchs = list(filter(lambda x: x is not None,
                map(lambda x: re.match(re_server, x), lines)))

        # Find server name specified in form: ypserver HOSTNAME
        mtchs.extend(list(filter(lambda x: x is not None,
                map(lambda x: re.match(re_ypserver, x), lines))))

        # Get hostnames from matches
        hostnames = list(map(lambda x: x.group(1), mtchs))

        # Get hostnames that are not IP addresses
        not_ips = list()
        for h in hostnames:
            try:
                ipaddress.ip_address(h)
            except ValueError:
                not_ips.append(h)

        return not_ips


    def process(self):

        # if NIS is not used for domainname resolution, everything is OK
        if not self.nis_in_nsswitch_hosts():
            return

        hostnames = self.hostnames_in_yp_conf()

        if len(hostnames) > 0:

            title = "Unsupported NIS configuration found"
            summary = "NIS may be used for domain name resolution only if NIS "\
                        "server is specified by IP. NIS servers specified by "\
                        "host name: {}".format(", ".join(hostnames))
            severity = "medium"
            report_generic(title = title, severity = severity, summary = summary)

