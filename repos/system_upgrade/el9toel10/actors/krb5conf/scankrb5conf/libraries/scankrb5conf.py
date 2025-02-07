import os

from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import CalledProcessError, run
from leapp.models import DistributionSignedRPM, OutdatedKrb5conf, RpmKrb5conf


def fetch_outdated_krb5_conf_files(conf_paths, ca_bundle_path='/etc/ssl/certs/ca-certificates.crt'):
    krb5_conf_files = set()
    outdated_rpm_conf = []
    outdated_conf = set()

    for conf_path in conf_paths:
        if os.path.isdir(conf_path):
            for conf_file in os.listdir(conf_path):
                krb5_conf_files.add(os.path.join(conf_path, conf_file))
        else:
            krb5_conf_files.add(conf_path)

    for file_path in krb5_conf_files:
        with open(file_path) as f:
            if -1 != f.read().find(ca_bundle_path):
                if file_path == '/etc/krb5.conf':
                    # The main krb5 config file is a special case. It is not
                    # modified by RPM updates, thus we have to use Leapp to do
                    # so.
                    outdated_conf.add(file_path)
                else:
                    try:
                        rpm_nvr = run(['/usr/bin/rpm', '-qf', file_path], split=True)['stdout'][0]
                        # We only want to handle files signed by the distribution, because we have no guarantees
                        # about third party packages (we assume updated versions are already available).
                        if not has_package(DistributionSignedRPM, rpm_nvr):
                            outdated_rpm_conf.append(RpmKrb5conf(path=file_path, rpm=rpm_nvr))
                    except CalledProcessError:
                        # Files not associated with any RPM are considered unmanaged.
                        outdated_conf.add(file_path)

    return OutdatedKrb5conf(unmanaged_files=list(outdated_conf),
                            rpm_provided_files=list(outdated_rpm_conf))
