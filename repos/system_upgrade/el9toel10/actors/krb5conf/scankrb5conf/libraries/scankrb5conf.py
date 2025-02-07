import os

from leapp.models import OutdatedKrb5confLocation

def fetch_outdated_krb5_conf_files(conf_paths):
    locations = set()
    krb5_conf_files = set()

    for conf_path in conf_paths:
        if os.path.isdir(conf_path):
            for conf_file in os.listdir(conf_path):
                krb5_conf_files.add(conf_file)
        else:
            krb5_conf_files.add(conf_path)

    for file_path in krb5_conf_files:
        with open(file_path) as f:
            if -1 != f.read().find('/etc/ssl/certs/ca-certificates.crt'):
                locations.add(file)

    return OutdatedKrb5confLocation(locations=list(locations))
