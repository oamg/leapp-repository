from leapp.libraries.stdlib import api
from leapp.models import PkgManagerInfo, RHUIInfo


def _set_releasever(releasever):
    releasever_path = '/etc/dnf/vars/releasever'

    with open(releasever_path, 'w') as fo:
        fo.write(releasever+'\n')


def process():
    target_version = api.current_actor().configuration.version.target

    pkg_facts = next(api.consume(PkgManagerInfo), None)
    rhui_facts = next(api.consume(RHUIInfo), None)

    if pkg_facts and pkg_facts.etc_releasever is not None or rhui_facts:
        # if "/etc/dnf/vars/releasever" file exists, or we are using RHUI, let's set it to our
        # target version.
        _set_releasever(target_version)
    else:
        api.current_logger().debug(
            'Skipping execution. "releasever" is not set in DNF/YUM vars directory and no RHUIInfo has '
            'been produced'
        )
