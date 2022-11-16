import os

from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepositoryFile, TargetOSInstallationImage


def produce_repofile_if_iso_used():
    target_iso_msgs_iter = api.consume(TargetOSInstallationImage)
    target_iso = next(target_iso_msgs_iter, None)

    if not target_iso:
        return

    if next(target_iso_msgs_iter, None):
        api.current_logger().warn('Received multiple TargetISInstallationImage messages, using the first one')

    # Mounting was successful, create a repofile to copy into target userspace
    repofile_entry_template = ('[{repoid}]\n'
                               'name={reponame}\n'
                               'baseurl={baseurl}\n'
                               'enabled=0\n'
                               'gpgcheck=0\n')

    repofile_content = ''
    for repo in target_iso.repositories:
        repofile_content += repofile_entry_template.format(repoid=repo.repoid,
                                                           reponame=repo.repoid,
                                                           baseurl=repo.baseurl)

    target_os_path_prefix = 'el{target_major_ver}'.format(target_major_ver=get_target_major_version())
    iso_repofile_path = os.path.join('/var/lib/leapp/', '{}_iso.repo'.format(target_os_path_prefix))
    with open(iso_repofile_path, 'w') as iso_repofile:
        iso_repofile.write(repofile_content)

    api.produce(CustomTargetRepositoryFile(file=iso_repofile_path))
