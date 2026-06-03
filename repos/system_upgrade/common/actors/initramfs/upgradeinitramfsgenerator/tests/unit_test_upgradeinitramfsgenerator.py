import os
import shutil

import pytest

from leapp.exceptions import StopActorExecutionError
from leapp.libraries.actor import upgradeinitramfsgenerator
from leapp.libraries.common.config import architecture
from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked, produce_mocked
from leapp.utils.deprecation import suppress_deprecation

from leapp.models import (  # isort:skip
    FIPSInfo,
    KernelInfo,
    RPM,
    RequiredUpgradeInitramPackages,  # deprecated
    UpgradeDracutModule,  # deprecated
    BootContent,
    CopyFile,
    DracutModule,
    KernelModule,
    MDArray,
    RAIDInfo,
    TargetUserSpaceUpgradeTasks,
    UpgradeInitramfsTasks,
)

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PKGS = ['pkg{}'.format(c) for c in 'ABCDEFGHIJ']
FILES = [
    CopyFile(src='/host/srcfile{}'.format(i), dst='/cont/dstfile{}'.format(i))
    for i in range(5)
]
MODULES = [
    ('moduleA', None),
    ('moduleB', None),
    ('moduleC', '/some/path/moduleC'),
    ('moduleD', '/some/path/moduleD'),
]


@pytest.fixture
def adjust_cwd():
    previous_cwd = os.getcwd()
    os.chdir(os.path.join(CUR_DIR, "../"))
    yield
    os.chdir(previous_cwd)


def _ensure_list(data):
    return data if isinstance(data, list) else [data]


def gen_TUSU(packages, copy_files=None):
    packages = _ensure_list(packages)

    if not copy_files:
        copy_files = []
    copy_files = _ensure_list(copy_files)

    return TargetUserSpaceUpgradeTasks(install_rpms=packages, copy_files=copy_files)


@suppress_deprecation(RequiredUpgradeInitramPackages)
def gen_RUIP(packages):
    packages = _ensure_list(packages)
    return RequiredUpgradeInitramPackages(packages=packages)


def gen_UIT(dracut_modules, kernel_modules, files):
    files = _ensure_list(files)

    dracut_modules = [DracutModule(name=i[0], module_path=i[1]) for i in _ensure_list(dracut_modules)]
    kernel_modules = [KernelModule(name=i[0], module_path=i[1]) for i in _ensure_list(kernel_modules)]

    return UpgradeInitramfsTasks(include_files=files,
                                 include_dracut_modules=dracut_modules,
                                 include_kernel_modules=kernel_modules,
                                 )


@suppress_deprecation(UpgradeDracutModule)
def gen_UDM_list(data):
    if not isinstance(data, list):
        data = [data]
    return [UpgradeDracutModule(name=i[0], module_path=i[1]) for i in data]


class MockedContext:
    def __init__(self):
        self.called_copy_from = []
        self.called_copytree_from = []
        self.called_copy_to = []
        self.called_call = []
        self.called_makedirs = []
        self.written_files = {}
        self.content = set()
        self.base_dir = "/base/dir"
        """
        Content (paths) that should exists regarding the used methods.

        It's not 100% same. Just dst paths are copied here. Ignoring differences
        between copy to /path/to/filename and /path/to/dirname which in real
        world could be different. For our purposes it's ok as it is now.

        Point is, that in case of use context.remove_tree(), we are able to
        detect whether something what is expected to be present is not missing.
        """

    def copy_from(self, src, dst):
        self.called_copy_from.append((src, dst))

    def copytree_from(self, src, dst):
        self.called_copytree_from.append((src, dst))

    def copy_to(self, src, dst):
        self.called_copy_to.append((src, dst))
        self.content.add(dst)

    def copytree_to(self, src, dst):
        self.called_copy_to.append((src, dst))
        self.content.add(dst)

    def makedirs(self, path, exists_ok=True):
        self.called_makedirs.append(path)

    def remove_tree(self, path):
        # make list for iteration as change of the set is expected during the
        # iteration, which could lead to runtime error
        for item in list(self.content):
            # ensure the / is the last character to simulate dirname
            dir_fmt_path = path if path[-1] == '/' else path + '/'
            if item == path or item.startswith(dir_fmt_path):
                # remove the file or everything inside dir (including dir)
                self.content.remove(item)

    def call(self, *args, **kwargs):
        self.called_call.append((args, kwargs))

    def full_path(self, path):
        return os.path.join(self.base_dir, os.path.abspath(path).lstrip('/'))

    def open(self, path, *args, mode='r', **kwargs):  # pylint: disable=no-self-use
        if 'w' not in mode:
            raise NotImplementedError('MockedContext.open only supports write mode')

        written_files = self.written_files
        contents = []

        class _Writer:
            def write(self, data):  # pylint: disable=no-self-use
                contents.append(data)

            def __enter__(self):
                return self

            def __exit__(self, *dummy):
                written_files[path] = ''.join(contents)

        return _Writer()


class MockedLogger(logger_mocked):

    def error(self, *args, **dummy):
        self.errmsg.extend(args)


@pytest.mark.parametrize('arch', architecture.ARCH_SUPPORTED)
def test_copy_boot_files(monkeypatch, arch):
    kernel = 'vmlinuz-upgrade.{}'.format(arch)
    kernel_hmac = '.vmlinuz-upgrade.{}.hmac'.format(arch)
    initram = 'initramfs-upgrade.{}.img'.format(arch)
    bootc = BootContent(
        kernel_path=os.path.join('/boot', kernel),
        kernel_hmac_path=os.path.join('/boot', kernel_hmac),
        initram_path=os.path.join('/boot', initram)
    )

    context = MockedContext()
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(arch=arch))
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'produce', produce_mocked())

    def create_upgrade_hmac_from_target_hmac_mock(original_hmac_path, upgrade_hmac_path, upgrade_kernel):
        hmac_file = '.{}.hmac'.format(upgrade_kernel)
        assert original_hmac_path == os.path.join(context.full_path('/artifacts'), hmac_file)
        assert upgrade_hmac_path == bootc.kernel_hmac_path

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        'create_upgrade_hmac_from_target_hmac',
                        create_upgrade_hmac_from_target_hmac_mock)

    actual_boot_content = upgradeinitramfsgenerator.copy_boot_files(context)
    assert len(context.called_copy_from) == 2
    assert (os.path.join('/artifacts', kernel), bootc.kernel_path) in context.called_copy_from
    assert (os.path.join('/artifacts', initram), bootc.initram_path) in context.called_copy_from

    assert actual_boot_content == bootc


class MockedCopyArgs:
    def __init__(self):
        self.args = None

    def __call__(self, *args):
        self.args = args


def _sort_files(copy_files):
    return sorted(copy_files, key=lambda x: (x.src, x.dst))


@pytest.mark.parametrize('raid_info,expected_path,expected_content', [
    (None, None, None),
    (RAIDInfo(md_arrays=[]), None, None),
    (
        RAIDInfo(md_arrays=[MDArray(uuid='aaa:bbb')]),
        upgradeinitramfsgenerator.LEAPP_CMDLINE_CONF_PATH,
        'rd.md.uuid=aaa:bbb\n',
    ),
    (
        RAIDInfo(md_arrays=[MDArray(uuid='aaa:bbb'), MDArray(uuid='ccc:ddd')]),
        upgradeinitramfsgenerator.LEAPP_CMDLINE_CONF_PATH,
        'rd.md.uuid=aaa:bbb rd.md.uuid=ccc:ddd\n',
    ),
])
def test_write_md_uuid_cmdline_conf(monkeypatch, raid_info, expected_path, expected_content):
    context = MockedContext()
    msgs = [raid_info] if raid_info is not None else []
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(msgs=msgs))
    result = upgradeinitramfsgenerator.write_md_uuid_cmdline_conf(context)

    assert result == expected_path
    if expected_path:
        assert '/etc/cmdline.d' in context.called_makedirs
        assert context.written_files[expected_path] == expected_content
    else:
        assert not context.written_files
        assert not context.called_makedirs


def test_generate_initram_disk_includes_md_cmdline_conf(monkeypatch):
    context = MockedContext()
    raid_info = RAIDInfo(md_arrays=[MDArray(uuid='aaa:bbb')])
    input_msgs = gen_UDM_list(MODULES[0]) + [raid_info]
    curr_actor = CurrentActorMocked(msgs=input_msgs, arch=architecture.ARCH_X86_64)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', curr_actor)
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_dracut_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_target_kernel_version', lambda _: '1.0-1.x86_64')
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_kernel_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_boot_files', lambda dummy: None)
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_fspace', MockedGetFspace(2*2**30))

    upgradeinitramfsgenerator.generate_initram_disk(context)

    assert context.written_files[upgradeinitramfsgenerator.LEAPP_CMDLINE_CONF_PATH] == 'rd.md.uuid=aaa:bbb\n'
    assert len(context.called_call) == 1
    shell_cmd = context.called_call[0][0][0][2]
    assert 'LEAPP_DRACUT_INSTALL_FILES="{path}"'.format(
        path=upgradeinitramfsgenerator.LEAPP_CMDLINE_CONF_PATH
    ) in shell_cmd
    assert 'LEAPP_DRACUT_MDADMCONF="1"' in shell_cmd


def test_prepare_userspace_for_initram_no_script(monkeypatch):
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'get_actor_file_path', lambda dummy: None)
    with pytest.raises(StopActorExecutionError) as err:
        upgradeinitramfsgenerator.prepare_userspace_for_initram(MockedContext())
    assert err.value.message == 'Mandatory script to generate initram not available.'


@pytest.mark.parametrize('input_msgs,pkgs,files', [
    # deprecated packages only, without files -- original functionality
    ([gen_RUIP([])], [], []),
    ([gen_RUIP(PKGS[0])], PKGS[0], []),
    ([gen_RUIP(PKGS)], PKGS, []),

    # packages only, without files -- new analogy to previous functionality
    ([gen_TUSU([])], [], []),
    ([gen_TUSU(PKGS[0])], PKGS[0], []),
    ([gen_TUSU(PKGS)], PKGS, []),

    # packages only, mix of deprecated and new models - same sets
    ([gen_RUIP([]), gen_TUSU([])], [], []),
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[0])], PKGS[0], []),
    ([gen_RUIP(PKGS), gen_TUSU(PKGS)], PKGS, []),

    # packages only, mix of deprecated and new models - disjoint sets
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[1])], PKGS[0:2], []),
    ([gen_RUIP([]), gen_TUSU(PKGS)], PKGS, []),
    ([gen_RUIP(PKGS), gen_TUSU([])], PKGS, []),
    ([gen_RUIP(PKGS[0:5]), gen_TUSU(PKGS[5:])], PKGS, []),

    # packages only, mix of deprecated and new models - mixed
    ([gen_RUIP(PKGS[0:7]), gen_TUSU(PKGS[5:])], PKGS, []),

    # files only
    ([gen_TUSU([], FILES[0])], [], FILES[0]),
    ([gen_TUSU([], FILES)], [], FILES),

    # packages and files
    ([gen_RUIP(PKGS[0]), gen_TUSU(PKGS[1], FILES)], PKGS[0:2], FILES),
    ([gen_RUIP(PKGS[0:7]), gen_TUSU(PKGS[5:], FILES)], PKGS, FILES),
])
def test_prepare_userspace_for_initram(monkeypatch, adjust_cwd, input_msgs, pkgs, files):
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', CurrentActorMocked(msgs=input_msgs))
    monkeypatch.setattr(upgradeinitramfsgenerator, '_install_initram_deps', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_copy_files', MockedCopyArgs())

    context = MockedContext()
    upgradeinitramfsgenerator.prepare_userspace_for_initram(context)

    # check the upgradeinitramfsgenerator script is copied into the container
    initram_copy = (
        upgradeinitramfsgenerator.api.get_actor_file_path(upgradeinitramfsgenerator.INITRAM_GEN_SCRIPT_NAME),
        os.path.join('/', upgradeinitramfsgenerator.INITRAM_GEN_SCRIPT_NAME)
    )
    assert initram_copy in context.called_copy_to

    # check the set of packages required to be installed matches expectations
    _pkgs = set(pkgs) if isinstance(pkgs, list) else set([pkgs])
    assert upgradeinitramfsgenerator._install_initram_deps.args[0] == _pkgs

    # check the set of files to be copied into the container matches exp
    _files = _sort_files(files) if isinstance(files, list) else [files]
    assert _sort_files(upgradeinitramfsgenerator._copy_files.args[1]) == _files


class MockedGetFspace:
    def __init__(self, space):
        self.space = space

    def __call__(self, dummy_path, convert_to_mibs=False):
        if not convert_to_mibs:
            return self.space
        return int(self.space / 1024 / 1024)


@pytest.mark.parametrize('input_msgs,dracut_modules,kernel_modules', [
    # test dracut modules with UpgradeDracutModule(s) - orig functionality
    (gen_UDM_list(MODULES[0]), MODULES[0], []),
    (gen_UDM_list(MODULES), MODULES, []),

    # test dracut modules with UpgradeInitramfsTasks - new functionality
    ([gen_UIT(MODULES[0], MODULES[0], [])], MODULES[0], MODULES[0]),
    ([gen_UIT(MODULES, MODULES, [])], MODULES, MODULES),

    # test dracut modules with old and new models
    (gen_UDM_list(MODULES[1]) + [gen_UIT(MODULES[2], [], [])], MODULES[1:3], []),
    (gen_UDM_list(MODULES[2:]) + [gen_UIT(MODULES[0:2], [], [])], MODULES, []),
    (gen_UDM_list(MODULES[1]) + [gen_UIT([], MODULES[2], [])], MODULES[1], MODULES[2]),
    (gen_UDM_list(MODULES[2:]) + [gen_UIT([], MODULES[0:2], [])], MODULES[2:], MODULES[0:2]),

    # TODO(pstodulk): test include files missing (relates #376)
])
def test_generate_initram_disk(monkeypatch, input_msgs, dracut_modules, kernel_modules):
    context = MockedContext()
    curr_actor = CurrentActorMocked(msgs=input_msgs, arch=architecture.ARCH_X86_64)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor', curr_actor)
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_dracut_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_target_kernel_version', lambda _: '5.14.0-100.el9.x86_64')
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_kernel_modules', MockedCopyArgs())
    monkeypatch.setattr(upgradeinitramfsgenerator, 'copy_boot_files', lambda dummy: None)
    monkeypatch.setattr(upgradeinitramfsgenerator, '_get_fspace', MockedGetFspace(2*2**30))
    upgradeinitramfsgenerator.generate_initram_disk(context)

    # TODO(pstodulk): add tests for the check of the free space (sep. from this func)

    # test now just that all modules have been passed for copying - so we know
    # all modules have been consumed
    detected_dracut_modules = set()
    _dracut_modules = set(dracut_modules) if isinstance(dracut_modules, list) else set([dracut_modules])
    for dracut_module in upgradeinitramfsgenerator.copy_dracut_modules.args[1]:
        module = (dracut_module.name, dracut_module.module_path)
        assert module in _dracut_modules
        detected_dracut_modules.add(module)
    assert detected_dracut_modules == _dracut_modules

    detected_kernel_modules = set()
    _kernel_modules = set(kernel_modules) if isinstance(kernel_modules, list) else set([kernel_modules])
    for kernel_module in upgradeinitramfsgenerator.copy_kernel_modules.args[1]:
        module = (kernel_module.name, kernel_module.module_path)
        assert module in _kernel_modules
        detected_kernel_modules.add(module)
    assert detected_kernel_modules == _kernel_modules

    assert upgradeinitramfsgenerator.copy_kernel_modules.args[2] == '5.14.0-100.el9.x86_64'

    # TODO(pstodulk): this test is not created properly, as context.call check
    # is skipped completely. Testing will more convenient with fixed #376
    # similar to the files...


def test_copy_dracut_modules_rmtree_ignore(monkeypatch):
    context = MockedContext()

    def raise_env_error(dummy):
        raise EnvironmentError('an error')

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    dmodules = [DracutModule(name='foo', module_path='/path/foo')]
    upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert context.content

    # env error should be ignored in this case
    context.content = set()
    context.remove_tree = raise_env_error
    upgradeinitramfsgenerator.copy_dracut_modules(context, dmodules)
    assert context.content


@pytest.mark.parametrize('kind', ['dracut', 'kernel'])
def test_copy_modules_fail(monkeypatch, kind):
    context = MockedContext()

    def copytree_to_error(src, dst):
        raise shutil.Error('myerror: {}, {}'.format(src, dst))

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    context.copytree_to = copytree_to_error
    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())

    module_class = None
    copy_fn = None
    dst_dir = None
    if kind == 'dracut':
        module_class = DracutModule
        copy_fn = upgradeinitramfsgenerator.copy_dracut_modules
        dst_dir = 'dracut'
    elif kind == 'kernel':
        module_class = KernelModule
        copy_fn = upgradeinitramfsgenerator.copy_kernel_modules
        dst_dir = 'lib/modules/dummy/extra/leapp'

    modules = [module_class(name='foo', module_path='/path/foo')]
    with pytest.raises(StopActorExecutionError) as err:
        if kind == 'dracut':
            copy_fn(context, modules)
        else:
            copy_fn(context, modules, 'dummy')
    assert err.value.message.startswith('Failed to install {kind} modules'.format(kind=kind))
    expected_err_log = 'Failed to copy {kind} module "foo" from "/path/foo" to "/base/dir/{dst_dir}"'.format(
            kind=kind, dst_dir=dst_dir)
    assert expected_err_log in upgradeinitramfsgenerator.api.current_logger.errmsg


@pytest.mark.parametrize('kind', ['dracut', 'kernel'])
def test_copy_modules_duplicate_skip(monkeypatch, kind):
    context = MockedContext()

    def mock_context_path_exists(path):
        full_path_content = {context.full_path(i) for i in context.content}
        return full_path_content.intersection(set([path, path + '/'])) != set()

    monkeypatch.setattr(os.path, 'exists', mock_context_path_exists)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_logger', MockedLogger())

    module_class = None
    copy_fn = None
    if kind == 'dracut':
        module_class = DracutModule
        copy_fn = upgradeinitramfsgenerator.copy_dracut_modules
    elif kind == 'kernel':
        module_class = KernelModule
        copy_fn = upgradeinitramfsgenerator.copy_kernel_modules

    module = module_class(name='foo', module_path='/path/foo')
    modules = [module, module]

    if kind == 'dracut':
        copy_fn(context, modules)
    else:
        copy_fn(context, modules, 'dummy')

    debugmsg = 'The foo {kind} module has been already installed. Skipping.'.format(kind=kind)
    assert context.content
    assert len(context.called_copy_to) == 1
    assert debugmsg in upgradeinitramfsgenerator.api.current_logger.dbgmsg


def test_create_upgrade_hmac_from_target_hmac(monkeypatch):
    upgrade_hmac_written = False

    def _read_file_mock(path):
        assert path == '/original-hmac'
        return ('ff00a9674033eea61bec48d21a1d2c27eaac9bd6ed4997e31dd0d9307c7a4770eb81df7116c'
                '4ace25d354a06dfdcd75e38f504f2ea7c1c4bdc95ea7083b701c0  vmlinuz-6.12.0-55.9.1.el10_0.x86_64')

    def _write_file_mock(path, content):
        assert path == '/boot/.vmlinuz-upgrade.x86_64.hmac'
        expected_content = ('ff00a9674033eea61bec48d21a1d2c27eaac9bd6ed4997e31dd0d9307c7a4770eb81df7116c'
                            '4ace25d354a06dfdcd75e38f504f2ea7c1c4bdc95ea7083b701c0  '
                            'vmlinuz-upgrade.x86_64\n')
        assert content == expected_content
        nonlocal upgrade_hmac_written
        upgrade_hmac_written = True

    monkeypatch.setattr(upgradeinitramfsgenerator, '_read_file', _read_file_mock)
    monkeypatch.setattr(upgradeinitramfsgenerator, '_write_file', _write_file_mock)
    upgradeinitramfsgenerator.create_upgrade_hmac_from_target_hmac(
        '/original-hmac', '/boot/.vmlinuz-upgrade.x86_64.hmac', 'vmlinuz-upgrade.x86_64')

    assert upgrade_hmac_written


def test_prepare_boot_files_for_livemode(monkeypatch):
    context_mock = MockedContext()

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        '_get_target_kernel_version',
                        lambda ctx: '6.18.3-100.fc42.x86_64')

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        'get_boot_artifact_names',
                        lambda: ('vmlinuz-upgrade.x86_64', 'initramfs-upgrade.x86_64.img'))

    upgrade_kernel_present = False
    initramfs_generated = False
    upgrade_initramfs_present = False
    upgrade_kernel_hmac_present = False

    def copy_target_kernel_mock(context, target_kernel_ver, kernel_artifact_name):
        nonlocal upgrade_kernel_present
        upgrade_kernel_present = True

    def _generate_initramfs_mock(context, userspace_initramfs_dest, target_kernel_ver):
        nonlocal initramfs_generated
        initramfs_generated = True

    def create_upgrade_hmac_from_target_hmac_mock(uspace_kernel_hmac_path,
                                                  upgrade_kernel_hmac_dest,
                                                  kernel_artifact_name):
        assert upgrade_kernel_hmac_dest == '/boot/.vmlinuz-upgrade.x86_64.hmac'
        nonlocal upgrade_kernel_hmac_present
        upgrade_kernel_hmac_present = True

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        'copy_target_kernel_from_userspace_into_boot',
                        copy_target_kernel_mock)

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        'create_upgrade_hmac_from_target_hmac',
                        create_upgrade_hmac_from_target_hmac_mock)

    monkeypatch.setattr(upgradeinitramfsgenerator,
                        '_generate_livemode_initramfs',
                        _generate_initramfs_mock)

    boot_content = upgradeinitramfsgenerator.prepare_boot_files_for_livemode(context_mock)

    upgrade_initramfs_present = context_mock.called_copy_from[0][1] == '/boot/initramfs-upgrade.x86_64.img'

    assert upgrade_kernel_present
    assert initramfs_generated
    assert upgrade_initramfs_present
    assert upgrade_kernel_hmac_present

    assert boot_content.kernel_path == '/boot/vmlinuz-upgrade.x86_64'
    assert boot_content.initram_path == '/boot/initramfs-upgrade.x86_64.img'
    assert boot_content.kernel_hmac_path == '/boot/.vmlinuz-upgrade.x86_64.hmac'


def _make_kernel_info(page_size='4k', arch='aarch64'):
    return KernelInfo(
        pkg=RPM(name='kernel-core', arch=arch, version='5.14.0', release='100.el9',
                epoch='0', packager='', pgpsig='SIG'),
        type='ordinary',
        uname_r='5.14.0-100.el9.{}'.format(arch),
        page_size=page_size,
    )


@pytest.mark.parametrize('page_size,arch,expected_pkg,expected_uname_r', [
    ('4k', 'aarch64', 'kernel-core', '5.14.0-100.el9.aarch64'),
    ('4k', 'x86_64', 'kernel-core', '5.14.0-100.el9.x86_64'),
    ('4k', 's390x', 'kernel-core', '5.14.0-100.el9.s390x'),
    # aarch64: 64k page size and special kernel packages
    ('64k', 'aarch64', 'kernel-64k-core', '5.14.0-100.el9.aarch64+64k'),
    # ppc64le: 64k page size but standard kernel packages
    ('64k', 'ppc64le', 'kernel-core', '5.14.0-100.el9.ppc64le'),
])
def test_get_target_kernel_version_page_size(monkeypatch, page_size, arch, expected_pkg, expected_uname_r):
    kernel_info = _make_kernel_info(page_size, arch)
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor',
                        CurrentActorMocked(arch=arch, msgs=[kernel_info]))

    context = MockedContext()
    target_nevra = '{}-5.14.0-100.el9.{}'.format(expected_pkg, arch)
    queried_cmds = []

    def mock_call(cmd, *args, **kwargs):
        queried_cmds.append(cmd)
        if cmd[:2] == ['rpm', '-qa']:
            return {'stdout': [target_nevra]}
        if cmd[:3] == ['rpm', '-q', '--provides']:
            return {'stdout': ['kernel-uname-r = {}'.format(expected_uname_r)]}
        return {'stdout': []}

    context.call = mock_call

    version = upgradeinitramfsgenerator._get_target_kernel_version(context)
    assert version == expected_uname_r
    assert queried_cmds[0] == ['rpm', '-qa', expected_pkg]
    assert queried_cmds[1] == ['rpm', '-q', '--provides', target_nevra]


def test_get_target_kernel_version_no_kernel_info(monkeypatch):
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor',
                        CurrentActorMocked(msgs=[]))

    context = MockedContext()

    with pytest.raises(StopActorExecutionError, match='Could not retrieve KernelInfo message'):
        upgradeinitramfsgenerator._get_target_kernel_version(context)


def test_get_target_kernel_version_empty_results(monkeypatch):
    kernel_info = _make_kernel_info(page_size='4k', arch='x86_64')
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', msgs=[kernel_info]))

    context = MockedContext()
    context.call = lambda cmd, *args, **kwargs: {'stdout': []}

    with pytest.raises(StopActorExecutionError, match='Cannot get version of the installed kernel'):
        upgradeinitramfsgenerator._get_target_kernel_version(context)


def test_get_target_kernel_version_empty_uname_r(monkeypatch):
    kernel_info = _make_kernel_info(page_size='4k', arch='x86_64')
    monkeypatch.setattr(upgradeinitramfsgenerator.api, 'current_actor',
                        CurrentActorMocked(arch='x86_64', msgs=[kernel_info]))

    context = MockedContext()

    def mock_call(cmd, *args, **kwargs):
        if cmd[:2] == ['rpm', '-qa']:
            return {'stdout': ['kernel-core-5.14.0-100.el9.x86_64']}
        if cmd[:3] == ['rpm', '-q', '--provides']:
            return {'stdout': ['some-other-provide = foo']}
        return {'stdout': []}

    context.call = mock_call

    with pytest.raises(StopActorExecutionError, match='Cannot get version of the installed kernel'):
        upgradeinitramfsgenerator._get_target_kernel_version(context)
