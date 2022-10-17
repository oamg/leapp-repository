import os

from leapp.libraries.stdlib import api
from leapp.models import CustomTargetRepository, TargetOSInstallationImage


def inform_ipu_about_request_to_use_target_iso():
    target_iso_path = os.getenv('LEAPP_DEVEL_TARGET_ISO')
    if not target_iso_path:
        return

    # TODO(mhecko): Add logic to extract what repositories can we find in the iso
    iso_mountpoint = '/iso'
    repo_dirs = ('BaseOS', 'AppStream')
    iso_repos = []
    for repo_dir in repo_dirs:
        baseurl = 'file://' + os.path.join(iso_mountpoint, repo_dir)
        iso_repo = CustomTargetRepository(name=repo_dir, baseurl=baseurl, repoid=repo_dir)
        api.produce(iso_repo)
        iso_repos.append(iso_repo)

    api.produce(TargetOSInstallationImage(path=target_iso_path,
                                          repositories=iso_repos,
                                          mountpoint=iso_mountpoint))
