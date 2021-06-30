import json
import os

from leapp.libraries.common import repofileutils

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


def test_invert_dict():
    input_dict = {1: ['a', 'b'], 2: ['b'], 3: []}
    inv_dict = repofileutils._invert_dict(input_dict)
    assert inv_dict == {'a': [1], 'b': [1, 2]}


def test_parse_repofile():
    repofile = repofileutils.parse_repofile(os.path.join(CUR_DIR, 'sample_repos.txt'))

    repo_appstream = [repo for repo in repofile.data if repo.repoid == 'AppStream'][0]
    assert repo_appstream.name == 'CentOS-$releasever - AppStream'
    assert repo_appstream.baseurl is None  # comments shouldn't get parsed
    assert repo_appstream.metalink is None
    assert repo_appstream.mirrorlist == ('http://mirrorlist.centos.org/?release=$releasever'
                                         '&arch=$basearch&repo=AppStream&infra=$infra')
    assert repo_appstream.enabled is True
    additional_appstream = json.loads(repo_appstream.additional_fields)
    assert additional_appstream['gpgcheck'] == '1'
    assert additional_appstream['gpgkey'] == 'file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial'
    assert additional_appstream['cost'] == '77'
    assert additional_appstream.get('baseurl') is None

    repo_leapp = [repo for repo in repofile.data if repo.repoid == 'leapp-copr'][0]
    assert repo_leapp.name == 'Copr repo for devel Leapp builds'
    assert repo_leapp.baseurl == 'http://coprbe.devel.redhat.com/results/oam-group/leapp/rhel-7-x86_64/'
    assert repo_leapp.metalink is None
    assert repo_leapp.mirrorlist is None
    assert repo_leapp.enabled is False
    additional_leapp = json.loads(repo_leapp.additional_fields)
    assert additional_leapp['type'] == 'rpm-md'
    assert additional_leapp['skip_if_unavailable'] == 'True'
    assert additional_leapp['gpgcheck'] == '0'
    assert additional_leapp['gpgkey'] == 'http://coprbe.devel.redhat.com/results/oam-group/leapp/pubkey.gpg'
    assert additional_leapp['repo_gpgcheck'] == '0'
    assert additional_leapp['enabled_metadata'] == '1'
    assert len(additional_leapp) == 6

    assert len([repo for repo in repofile.data if repo.repoid == 'spe-ci_al.cha:rs']) == 1

    repos_duplicate = [repo for repo in repofile.data if repo.repoid == 'duplicate']
    assert len(repos_duplicate) == 1  # only one instance got through
    assert repos_duplicate[0].name == 'Duplicate 2'  # and it's the latter one
