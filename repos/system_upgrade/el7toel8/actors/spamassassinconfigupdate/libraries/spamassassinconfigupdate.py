from leapp.libraries.actor import (
    spamassassinconfigupdate_backup,
    spamassassinconfigupdate_spamc,
    spamassassinconfigupdate_spamd
)


class FileOperations(object):
    def read(self, path):
        with open(path, 'r') as f:
            return f.read()

    def write(self, path, content):
        with open(path, 'w') as f:
            f.write(content)


def migrate_configs(facts, fileops=FileOperations(),
                    backup_func=spamassassinconfigupdate_backup.backup_file):
    """
    Perform necessary changes in spamassassin configuration. See
    lib_spamc.migrate_spamc_config() and lib_spamd.migrate_spamd_config for details.
    """
    spamassassinconfigupdate_spamc.migrate_spamc_config(facts, fileops, backup_func)
    spamassassinconfigupdate_spamd.migrate_spamd_config(facts, fileops, backup_func)
