import os
import re

BrlttyConf = '/etc/brltty.conf'


def check_for_unsupported_cfg():
    migrate_file = None
    migrate_bt = False
    migrate_espeak = False
    regex_bt = re.compile(r'\b((bth)|(bluez))([:\-][0-9a-fA-F]{2}){6}\b')
    regex_espeak = re.compile(r'^\s*speech-driver\s+es\b')
    if os.path.exists(BrlttyConf):
        with open(BrlttyConf) as file_check:
            for line in file_check:
                if regex_bt.search(line):
                    migrate_bt = True
                if regex_espeak.search(line):
                    migrate_espeak = True
                if migrate_bt and migrate_espeak:
                    break
    migrate_file = BrlttyConf if migrate_espeak or migrate_bt else ''
    return (migrate_file, migrate_bt, migrate_espeak)
