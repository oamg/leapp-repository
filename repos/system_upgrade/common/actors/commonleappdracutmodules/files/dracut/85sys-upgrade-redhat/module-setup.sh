#!/bin/bash

# Variable not used at the moment; would be needed in case of a remote upgrade
#LEAPPBIN=/usr/bin/leapp

check() {
    require_binaries base64 || return 1
    require_binaries tar || return 1
    require_binaries xz || return 1
    require_binaries md5sum || return 1
    require_binaries wc || return 1
    require_binaries grep || return 1
    # 0 enables by default, 255 only on request
    return 0
}

depends() {
    # we don't need plymouth, but in case it is part of initramfs, would be
    # better to do remove of some files (to ensure it will not annoy us)
    # after it is installed, so keep the dependency at least for now
    echo plymouth
}

install() {
    # stuff we need for initial boot
    # ------------------------------
    # SELinux policy and contexts
    # NOTE: try to remove that
    #dracut_install /etc/selinux/config
    #dracut_install /etc/selinux/*/policy/*
    #dracut_install $(find /etc/selinux/*/contexts)

    # shellcheck disable=SC2154 # Following variables are assigned by dracut
    { # NOTE: use these new variables instead to avoid the warning
    local _initdir=$initdir
    local _moddir=$moddir
    }

    # NOTE: rather remove it then keep it; we really don't want plymouth now
    #       (hopefully forever)
    # remove the plymouth text plugin so we get either graphics or details
    rm -rf "${_initdir}/$(plymouth --get-splash-plugin-path)text.so" \
           "${_initdir}"/usr/share/plymouth/themes/text/*


    # stuff we use in upgrade hook(s)
    # -------------------------------

    # NOTE: not needed probably, but we would need that later in case of
    #      remote upgrade
    # NOTE2: and it's script; not binary - use inst_script maybe?
    # upgrader binary
    #inst_binary $LEAPPBIN

    # config file so we can find it
    #mkdir -p "${initdir}/etc/conf.d"
    #echo "LEAPPBIN=$LEAPPBIN" > "${initdir}/etc/conf.d/redhat-upgrade-tool.conf"

    # NOTE: keep it for now
    # RPM hash/sig checks (via NSS) don't work without these
    #inst_libdir_file "libfreebl*" "libsqlite*" "libsoftokn*"

    # NOTE: do we need that? I guess that not as we will not use rpm like that
    # RPM can't find the rpmdb without rpmconfig
    #rpmconfig=$(find /etc/rpm /usr/lib/rpm -name "rpmrc" -o -name "macros*")
    #dracut_install $rpmconfig

    # !! NOTE !!
    # we need to put here much more energy later as it will be much reliable
    # to keep everything pre-pivot. Even the leapp itself should be ideally
    # part of the initramfs and we should install there all deps to be sure
    # we will not be *ucked up by missing/changed libraries during the upgrade.
    # As we discussed with gazdown, maybe we should keep that on actors itself
    # to say whether they should be run from the chrooted sys or outside
    # - just from the initamfs. This is specific really just for actors that
    # will be processed during the "offline" phases. From this point, maybe
    # function in a common library would be fine to help with that. But it's
    # probably not so easy to decide & realize how we will resolve that. Let's
    # keep that for discussion
    # Q: Would we hack that in way of copy whole initramfs into the root, mount
    #    mount it and set envars

    # install this one to ensure we are able to sync write
    inst_binary sync
    # install in-band debugging utilities
    inst_binary base64
    inst_binary tar
    inst_binary xz
    inst_binary md5sum
    inst_binary wc

    # to be able to check what RHEL X we boot in (target system)
    inst_binary grep

    # script to actually run the upgrader binary
    inst_hook upgrade 49 "$_moddir/mount_usr.sh"
    inst_hook upgrade 50 "$_moddir/do-upgrade.sh"

    #NOTE: some clean up?.. ideally, everything should be inside the leapp*
    #NOTE: current *.service is changed so in case we would like to use the
    #      hook, we will have to modify it back
    # it is always fine to have separate logs
    #inst_hook upgrade-post 99 "$moddir/save-journal.sh"
}
