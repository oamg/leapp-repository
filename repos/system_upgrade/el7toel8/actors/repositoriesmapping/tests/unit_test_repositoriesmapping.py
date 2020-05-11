import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import repositoriesmapping
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import produce_mocked, CurrentActorMocked
from leapp.libraries.stdlib import api
from leapp.models import EnvVar, RepositoriesMap, RepositoryMap

PRODUCT_TYPE = ['ga', 'beta', 'htb']


class ReadRepoFileMock(object):
    def __init__(self, repomap_data):
        self.repomap_file = self._gen_data_file(repomap_data)

    def __call__(self, dummy_filename):
        return self.repomap_file

    def _gen_data_file(self, repomap_data):
        """
        Generate the expected repomap file (list of strings - string per line).

        :param repomap_data: Data required to be able to generate repomap data
        :type repomap_data: list of tuples - tuple per repomap record
          [(from_repoid, to_repoid, to_pes_repo,
            from_minor_version, to_minorversion,
            arch, repo_type, src_prod_type, dst_prod_type)]
        """
        header = ('RHEL 7 repoid in CDN,RHEL 8 repoid in CDN,RHEL 8 repo name in PES,'
                  'RHEL 7 minor versions,RHEL 8 minor versions,architecture,'
                  'type(rpm/srpm/debuginfo),src repo type (ga/beta/htb),dst repo type (ga/beta/htb)')
        return [header] + [','.join(i) for i in repomap_data]


def gen_input_permutation():
    """Generate permutation of input parameters."""
    return [(arch, src, dst) for arch in architecture.ARCH_ACCEPTED for src in PRODUCT_TYPE for dst in PRODUCT_TYPE]


def gen_repomap_record(arch, src_type, dst_type, index=0):
    """Generate repomap record based on given data."""
    return ('src-repoid-{}-{}-{}'.format(arch, src_type, index),
            'dst-repoid-{}-{}-{}'.format(arch, dst_type, index),
            'pes-name', 'all', 'all', arch, 'rpm', src_type, dst_type)


def gen_test_data(arch, src_type, dst_type):
    """
    Generate testing data and return records related to the given params.

    By the related record (or expected_records) it's meant record we expect
    will be returned for specific arch and product types.

    :return: ([all_records], [expected_records])
    """
    generic_repomap_data = []
    expected_repomap_data = []
    for _arch, _src_type, _dst_type in gen_input_permutation():
        for i in range(2):
            record = gen_repomap_record(_arch, _src_type, _dst_type, i)
            generic_repomap_data.append(record)
            if _arch == arch and _src_type == src_type and _dst_type == dst_type:
                expected_repomap_data.append(record)
    return generic_repomap_data, expected_repomap_data


def gen_RepositoriesMap(repomap_records):
    """Generate Repositories map from the given repomap records."""
    repositories = []
    for record in repomap_records:
        repositories.append(RepositoryMap(
                    from_repoid=record[0],
                    to_repoid=record[1],
                    to_pes_repo=record[2],
                    from_minor_version=record[3],
                    to_minor_version=record[4],
                    arch=record[5],
                    repo_type=record[6]
        ))
    return RepositoriesMap(repositories=repositories)


@pytest.mark.parametrize('arch,src_type,dst_type', gen_input_permutation())
def test_scan_valid_file_without_comments(monkeypatch, arch, src_type, dst_type):
    envars = {'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': src_type, 'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': dst_type}
    input_data, expected_records = gen_test_data(arch, src_type, dst_type)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch, envars))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    repositoriesmapping.scan_repositories(read_repofile_func=ReadRepoFileMock(input_data))
    assert api.produce.called == 1
    assert api.produce.model_instances == [gen_RepositoriesMap(expected_records)]


# one combination is probably enough, as it's tested properly above
@pytest.mark.parametrize('arch,src_type,dst_type', [(architecture.ARCH_X86_64, PRODUCT_TYPE[0], PRODUCT_TYPE[0])])
def test_scan_valid_file_with_comments(monkeypatch, arch, src_type, dst_type):
    envars = {'LEAPP_DEVEL_SOURCE_PRODUCT_TYPE': src_type, 'LEAPP_DEVEL_TARGET_PRODUCT_TYPE': dst_type}
    input_data, expected_records = gen_test_data(arch, src_type, dst_type)
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(arch, envars))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    # add one comment and one empty line into the repomap file
    repofile = ReadRepoFileMock(input_data)
    repofile.repomap_file.insert(2, '')
    repofile.repomap_file.insert(3, '# comment')
    # run
    repositoriesmapping.scan_repositories(read_repofile_func=repofile)
    assert api.produce.called == 1
    assert api.produce.model_instances == [gen_RepositoriesMap(expected_records)]


@pytest.mark.parametrize('isFile,err_summary', [
    (False, 'The repository mapping file not found'),
    (True, 'The repository mapping file is invalid'),
])
def test_scan_missing_or_empty_file(monkeypatch, isFile, err_summary):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    monkeypatch.setattr('os.path.isfile', lambda dummy: isFile)
    if isFile:
        monkeypatch.setattr('os.path.getsize', lambda dummy: 0)
    with pytest.raises(StopActorExecutionError) as err:
        repositoriesmapping.scan_repositories()
    assert not api.produce.called
    assert err_summary in str(err)


@pytest.mark.parametrize('line', [
    'whatever invalid line',
    'something, jaj',
    'a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v',
    'valid,',
    '7-server-rpms,8-server-rpms,name-8-repo-rpms,all,all,x86_64,rpm',
    '7-server-rpms,8-server-rpms,name-8-repo-rpms,all,all,x86_64,rpm,ga,ga,invalid',
])
def test_scan_invalid_file_csv(monkeypatch, line):
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(architecture.ARCH_X86_64))
    monkeypatch.setattr(api, 'produce', produce_mocked())
    with pytest.raises(StopActorExecutionError) as err:
        repositoriesmapping.scan_repositories(read_repofile_func=ReadRepoFileMock([line]))
    assert not api.produce.called
    assert 'The repository mapping file is invalid' in str(err)
