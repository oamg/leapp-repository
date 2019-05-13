import re
import shutil

BackupSuffix = '.bak'


def migrate_file(fn, migrate_bt, migrate_espeak):
    # nothing to migrate
    if not fn or (not migrate_bt and not migrate_espeak):
        return

    # make backup
    shutil.copy2(fn, fn + BackupSuffix)

    regex_bt = re.compile(r'\b(?:(?:bth)|(?:bluez))((?:[:\-][0-9a-fA-F]{2}){6})\b')
    regex_espeak = re.compile(r'^(\s*speech-driver\s+)es\b')

    with open(fn, 'w') as file_out:
        with open(fn + BackupSuffix) as file_in:
            for line in file_in:
                if migrate_bt and regex_bt.search(line):
                    line = regex_bt.sub(r'bluetooth\1', line)
                elif migrate_espeak and regex_espeak.search(line):
                    line = regex_espeak.sub(r'\1en', line)
                file_out.write(line)
