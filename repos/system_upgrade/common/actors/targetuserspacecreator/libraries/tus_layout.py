"""
On-disk layout, scratch/overlay/nspawn setup, and the dev-only persistent
package cache for the ``targetuserspacecreator`` actor (§5, §12).

:func:`compute` resolves all the paths the actor works with (honouring
``LEAPP_CONTAINER_ROOT``) and the reserved free space for the overlay.
:func:`scratch_container` is the context manager that builds the source overlay,
optionally mounts the target ISO into the container root, and enters the result
as an nspawn scratch container - guaranteeing reverse-order teardown.

Leaf module: imports only shared leapp libraries and ``tus_constants``.
"""

import contextlib
import os

from leapp.libraries.actor import tus_constants
from leapp.libraries.common import mounting, overlaygen
from leapp.libraries.common.config import get_env
from leapp.libraries.common.config.version import get_target_major_version
from leapp.libraries.stdlib import api, run

_PERSISTENT_PACKAGE_CACHE_ENV = 'LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE'


class Layout(object):
    """Plain value object describing where the actor builds the userspace."""

    def __init__(self, container_root, target_major, userspace_path,
                 scratch_dir, mounts_dir, scratch_reserve):
        self.container_root = container_root
        self.target_major = target_major
        self.userspace_path = userspace_path
        self.scratch_dir = scratch_dir
        self.mounts_dir = mounts_dir
        self.scratch_reserve = scratch_reserve


def compute():
    """Resolve the on-disk layout and the recommended overlay free-space reserve."""
    container_root = get_env('LEAPP_CONTAINER_ROOT', tus_constants.DEFAULT_CONTAINER_ROOT)
    target_major = get_target_major_version()

    userspace_dirname = tus_constants.USERSPACE_DIRNAME_TEMPLATE.format(target_major=target_major)
    userspace_path = os.path.join(container_root, userspace_dirname)
    scratch_dir = os.path.join(container_root, 'scratch')
    mounts_dir = os.path.join(scratch_dir, 'mounts')

    scratch_reserve = overlaygen.get_recommended_leapp_free_space(userspace_path)

    return Layout(
        container_root=container_root,
        target_major=target_major,
        userspace_path=userspace_path,
        scratch_dir=scratch_dir,
        mounts_dir=mounts_dir,
        scratch_reserve=scratch_reserve,
    )


@contextlib.contextmanager
def scratch_container(layout, inputs):
    """
    Establish the scratch container and yield an entered nspawn context (§5).

    Nesting (each layer torn down in reverse order on exit):
      source overlay  ->  optional target-ISO mount into the container root
                      ->  nspawn into the overlay.

    :param layout: The :class:`Layout` produced by :func:`compute`.
    :param inputs: The :class:`~.tus_inputdata.InputData` value object.
    :yields: An entered ``mounting.NspawnActions`` scratch context.
    """
    with overlaygen.create_source_overlay(
        mounts_dir=layout.mounts_dir,
        scratch_dir=layout.scratch_dir,
        xfs_info=inputs.xfs_presence,
        storage_info=inputs.storage_info,
        scratch_reserve=layout.scratch_reserve,
    ) as overlay:
        # NullMount (a no-op) is returned when no ISO is present, so this is safe
        # to enter unconditionally.
        with mounting.mount_upgrade_iso_to_root_dir(overlay.target, inputs.target_iso):
            with overlay.nspawn() as scratch:
                yield scratch


def _persistent_cache_dir(layout):
    return os.path.join(
        layout.container_root,
        'el{}_persistent_package_cache'.format(layout.target_major)
    )


def _persistent_cache_enabled():
    return get_env(_PERSISTENT_PACKAGE_CACHE_ENV, '0') == '1'


# FIXME The caches shouldn't work with installroot
def persistent_cache_pull(context, layout, installroot):
    """
    Restore a previously stored dnf package cache into the installroot (§12, dev only).

    No-op unless ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``. Must be called
    after the installroot has been (re)created and before ``dnf install``. The
    persistent store lives on the real host; the installroot lives inside the
    build overlay, so the copy goes host → container.
    """
    if not _persistent_cache_enabled():
        return
    cache = _persistent_cache_dir(layout)
    if not os.path.isdir(cache):
        return
    dst = os.path.join(installroot, 'var', 'cache', 'dnf')
    api.current_logger().info('Restoring persistent dnf package cache into the userspace.')
    context.makedirs(os.path.dirname(dst), exists_ok=True)
    context.remove_tree(dst)
    context.copytree_to(cache, dst)


def persistent_cache_push(context, layout, installroot):
    """
    Store the installroot dnf package cache in the persistent store (§12, dev only).

    No-op unless ``LEAPP_DEVEL_USE_PERSISTENT_PACKAGE_CACHE=1``. Must be called
    after a successful build so the cache can be reused on the next run. The copy
    goes container → host.
    """
    if not _persistent_cache_enabled():
        return
    src = os.path.join(installroot, 'var', 'cache', 'dnf')
    if not os.path.isdir(context.full_path(src)):
        return
    cache = _persistent_cache_dir(layout)
    api.current_logger().info('Storing the userspace dnf package cache for reuse.')
    run(['rm', '-rf', cache])
    context.copytree_from(src, cache)
