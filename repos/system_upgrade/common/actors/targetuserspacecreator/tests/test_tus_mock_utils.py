"""
Shared mock helpers for the ``target_userspace_creator`` actor unit tests.

This module intentionally contains no test functions - it is a helper library
imported by the ``test_tus_*.py`` suites to avoid duplicating the same mock
classes/factories across files. It is named ``test_*`` only so it sits next to
the tests; pytest collects it and simply finds nothing to run.
"""

import os

from leapp.libraries.stdlib import CalledProcessError
from leapp.models import RHUIInfo, TargetRHUIPostInstallTasks, TargetRHUIPreInstallTasks, TargetRHUISetupInfo


class _MockFileHandle:
    """File handle returned by :meth:`MockContext.open`; accumulates writes."""

    def __init__(self, store, path):
        self._store = store
        self._path = path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def write(self, data):
        self._store[self._path] = self._store.get(self._path, '') + data


class MockContext:
    """
    Generic stand-in for ``mounting.IsolatedActions`` / the nspawn scratch context.

    Records every mutating call and returns configurable results. Covers the
    common surface shared by the content-access, rhui and userspace-build suites.
    Suites that need bespoke behaviour (e.g. simulating ``rpm -qf`` ownership)
    keep their own local context instead.
    """

    def __init__(self, base_dir='/base', call_result=None, raise_on_call=None, open_raises=None):
        self.base_dir = base_dir
        self.call_result = call_result
        self.raise_on_call = raise_on_call
        self._open_raises = open_raises
        self.calls = []
        self.copy_to_calls = []
        self.copytree_to_calls = []
        self.remove_calls = []
        self.remove_tree_calls = []
        self.makedirs_calls = []
        self.written_files = {}

    def full_path(self, path):
        return os.path.join(self.base_dir, path.lstrip('/'))

    def call(self, cmd, split=False, callback_raw=None):
        self.calls.append(cmd)
        if self.raise_on_call:
            raise self.raise_on_call
        if self.call_result is not None:
            return self.call_result
        return {'stdout': '', 'stderr': ''}

    def copy_to(self, src, dst):
        self.copy_to_calls.append((src, dst))

    def copytree_to(self, src, dst):
        self.copytree_to_calls.append((src, dst))

    def remove(self, path):
        self.remove_calls.append(path)

    def remove_tree(self, dst):
        self.remove_tree_calls.append(dst)

    def makedirs(self, path, exists_ok=False):
        self.makedirs_calls.append((path, exists_ok))

    def open(self, path, mode):
        if self._open_raises:
            raise self._open_raises
        return _MockFileHandle(self.written_files, path)


def make_cpe(message='Command failed', command=None, stdout='', stderr='error', exit_code=1):
    """Build a :class:`CalledProcessError` with the real 3-argument signature."""
    return CalledProcessError(
        message,
        command if command is not None else ['some', 'cmd'],
        {'stdout': stdout, 'stderr': stderr, 'exit_code': exit_code},
    )


def _make_setup_info(bootstrap=True, enable_only=True, preinstall_copies=None,
                     files_to_remove=None, postinstall_copies=None, supporting=None):
    """Build a :class:`TargetRHUISetupInfo` with test-friendly defaults."""
    preinstall = TargetRHUIPreInstallTasks(
        files_to_remove=files_to_remove or [],
        files_to_copy_into_overlay=preinstall_copies or [],
    )
    postinstall = TargetRHUIPostInstallTasks(files_to_copy=postinstall_copies or [])
    return TargetRHUISetupInfo(
        enable_only_repoids_in_copied_files=enable_only,
        preinstall_tasks=preinstall,
        postinstall_tasks=postinstall,
        files_supporting_client_operation=supporting or [],
        bootstrap_target_client=bootstrap,
    )


def make_rhui_info(bootstrap=True, enable_only=True, preinstall_copies=None,
                   src_pkgs=None, target_pkgs=None, files_to_remove=None,
                   postinstall_copies=None, supporting=None):
    """Build a :class:`RHUIInfo` wrapping :func:`_make_setup_info`."""
    setup = _make_setup_info(
        bootstrap=bootstrap,
        enable_only=enable_only,
        preinstall_copies=preinstall_copies,
        files_to_remove=files_to_remove,
        postinstall_copies=postinstall_copies,
        supporting=supporting,
    )
    return RHUIInfo(
        provider='aws',
        src_client_pkg_names=src_pkgs if src_pkgs is not None else ['src-client'],
        target_client_pkg_names=target_pkgs if target_pkgs is not None else ['target-client'],
        target_client_setup_info=setup,
    )


class MockInputData:  # pylint: disable=too-many-arguments
    """
    Stand-in for :class:`tus_inputdata.InputData` (the actor's input value object).

    Mirrors the real attribute set so every ``test_tus_*`` suite can share one
    mock. ``target_repositories`` is first so existing positional callers keep
    working; everything else is keyword-only in practice.
    """

    def __init__(self, target_repositories=None, storage_info=None, custom_repofiles=None,
                 rhsm_info=None, rhui_info=None, target_iso=None, preupgrade_tasks=None,
                 repositories_facts=None, pkg_manager_info=None, skip_rhsm=False,
                 nogpgcheck=False, packages=None, copy_files=None):
        self.target_repositories = target_repositories
        self.storage_info = storage_info
        self.rhsm_info = rhsm_info
        self.rhui_info = rhui_info
        self.target_iso = target_iso
        self.repositories_facts = repositories_facts
        self.pkg_manager_info = pkg_manager_info
        self.skip_rhsm = skip_rhsm
        self.nogpgcheck = nogpgcheck
        self.custom_repofiles = custom_repofiles or []
        self.preupgrade_tasks = preupgrade_tasks or []
        self.copy_files = copy_files or []
        self.packages = packages or set()


class RunSpy:
    """Callable spy recording every ``cmd`` passed to a module-level ``run``/``call``."""

    def __init__(self):
        self.calls = []

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append(cmd)
        return {'stdout': '', 'stderr': ''}


class MockNspawnActions:
    """Context-manager stand-in for ``mounting.NspawnActions``."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
