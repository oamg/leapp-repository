import os

from leapp.models import OutdatedKrb5confLocation


def fetch_outdated_krb5_conf_files(conf_paths, ca_bundle_path='/etc/ssl/certs/ca-certificates.crt'):
    locations = set()
    krb5_conf_files = set()

    for conf_path in conf_paths:
        if os.path.isdir(conf_path):
            for conf_file in os.listdir(conf_path):
                krb5_conf_files.add(os.path.join(conf_path, conf_file))
        else:
            krb5_conf_files.add(conf_path)

    for file_path in krb5_conf_files:
        with open(file_path) as f:
            if -1 != f.read().find(ca_bundle_path):
                locations.add(file_path)

    return OutdatedKrb5confLocation(locations=list(locations))
