import ipaddress
import os
import re
import shutil

from six import text_type

BackupSuffix = '.bak'

# false positives blacklist
rfp = re.compile(r'(^\s*RIPv6:::1\b)|(@\s+\[IPv6:::1\]\s+>)')

rs = re.compile(r'IPv6:[0-9a-fA-F:]*::[0-9a-fA-F:]*')


def uncompress_ipv6(ipv6):
    addr = text_type(ipv6.replace('IPv6:', ''))
    try:
        addr = 'IPv6:' + ipaddress.ip_address(addr).exploded
    except ValueError:
        addr = ipv6
    return re.sub(r':0([^:])', r':\1', re.sub(r'0+', r'0', addr))


def check_false_positives(f, l):
    return f in ['sendmail.cf', 'submit.cf'] and rfp.search(l) is not None


def sub_ipv6(m):
    return uncompress_ipv6(m.group(0))


def migrate_file(fn):
    # make backup
    shutil.copy2(fn, fn + BackupSuffix)
    with open(fn, 'w') as file_out:
        with open(fn + BackupSuffix) as file_in:
            for line in file_in:
                if rs.search(line) and not check_false_positives(os.path.basename(fn), line):
                    line = rs.sub(sub_ipv6, line)
                file_out.write(line)
