import os

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import CalledProcessError, run
from leapp.models import DistributionSignedRPM, OutdatedKrb5conf, RpmKrb5conf


def fetch_outdated_krb5_conf_files(conf_paths, ca_bundle_path='/etc/ssl/certs/ca-certificates.crt'):
    krb5_conf_files = set()
    odtd_rpm_conf = set()
    odtd_conf = set()

    for conf_path in conf_paths:
        if os.path.isdir(conf_path):
            for conf_file in os.listdir(conf_path):
                krb5_conf_files.add(os.path.join(conf_path, conf_file))
        else:
            krb5_conf_files.add(conf_path)

    for file_path in krb5_conf_files:
        with open(file_path) as f:
            if -1 != f.read().find(ca_bundle_path):
                try:
                    rpm_nvr = run(['/usr/bin/rpm', '-qf', file_path], split=True)['stdout']
                    if not has_package(DistributionSignedRPM, rpm_nvr):
                        odtd_rpm_conf.add(RpmKrb5conf(path=file_path, rpm=rpm_nvr))
                except CalledProcessError:
                    odtd_conf.add(file_path)

    return OutdatedKrb5conf(unmanaged_files=list(odtd_conf),
                            rpm_provided_files=list(odtd_rpm_conf))
