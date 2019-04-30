import os
import re

SendmailConfDir = '/etc/mail'
SendmailConfFiles = ['sendmail.cf', 'sendmail.mc', 'submit.cf', 'submit.mc']
# false positives blacklist
rfp = re.compile(r'(^\s*RIPv6:::1\b)|(@\s+\[IPv6:::1\]\s+>)')


def get_conf_files():
    conf_files = [os.path.join(SendmailConfDir, f) for f in SendmailConfFiles]
    return conf_files


def check_false_positives(filename, line):
    return filename in ['sendmail.cf', 'submit.cf'] and rfp.search(line) is not None


def check_files_for_compressed_ipv6():
    conf_files = get_conf_files()
    migrate_files = []
    files = [os.path.join(SendmailConfDir, re.sub(r'\.db$', '', f)) for f in os.listdir(SendmailConfDir)
             if f.endswith('.db')] + conf_files
    regex = re.compile(r'IPv6:[0-9a-fA-F:]*::')
    for filename in files:
        if not os.path.exists(filename):
            continue
        with open(filename) as file_check:
            for line in file_check:
                if regex.search(line) and not check_false_positives(os.path.basename(filename), line):
                    migrate_files.append(filename)
                    break
    return migrate_files
