#!/bin/bash
# ex: ts=8 sw=4 sts=4 et filetype=sh

# we need only one hook here as the rest will be processed by the leapp tool
# NOTE: in case we would like to do switch into the sysroot, would be better
#       to have upgrade-post hook as well maybe, but we should be able to do
#       that inside leapp as well..
# NOTE: for each hook here should be created script + systemd unit file
upgrade_hooks="upgrade"

check() {
    hookdirs+="$upgrade_hooks "
    return 255
}

depends() {
    echo "systemd"
    # NOTE: keep it for now as maybe we would like to use it later for our
    # purposes as well, but probably we will not need that.. just for now
    # keep it and look at "sys-upgrade"..
    #   (to recognize it from system-upgrade modules that would be installed)
    # pull in any other "sys-upgrade-*" modules that exist
    #local mod_dir mod
    #for mod_dir in $dracutbasedir/modules.d/[0-9][0-9]*; do
    #    [ -d $mod_dir ] || continue
    #    mod=${mod_dir##*/[0-9][0-9]}
    #    strstr "$mod" "sys-upgrade-" && echo $mod
    #done
    echo "sys-upgrade-redhat"
    return 0
}

install() {
    # NOTE: 98systemd copies units from here to /run/systemd/system so systemd
    #       won't lose our units after switch-root.
    unitdir="/etc/systemd/system"

    # shellcheck disable=SC2154 # Following variables are assigned by dracut
    { # NOTE: use these new variables instead to avoid the warning
    local _initdir=$initdir
    local _moddir=$moddir
    local _systemdsystemunitdir=$systemdsystemunitdir
    }

    # Set up systemd target and units
    upgrade_wantsdir="${_initdir}${unitdir}/upgrade.target.wants"

    inst_simple "${_moddir}/upgrade.target" "${unitdir}/upgrade.target"

    mkdir -p "$upgrade_wantsdir"
    for s in $upgrade_hooks; do
        inst_simple "${_moddir}/${s}.service" "${unitdir}/${s}.service"
        inst_script "${_moddir}/${s}.sh"      "/bin/$s"
        ln -sf "../${s}.service" "$upgrade_wantsdir"
    done

    # just try : set another services into the wantsdir
    #        sysroot.mount    \
    #        dracut-mount     \
    #        dracut-pre-udev  \
    #         dracut-pre-mount.service
    for s in \
             dracut-cmdline.service   \
             dracut-initqueue.service \
    ;do
        ln -sf "${_systemdsystemunitdir}/$s" "$upgrade_wantsdir"
    done

    # generator to switch to upgrade.target when we return to initrd
    generatordir="/usr/lib/systemd/system-generators"
    mkdir -p "${_initdir}${generatordir}"
    inst_script "${_moddir}/initrd-system-upgrade-generator" \
                "${generatordir}/initrd-system-upgrade-generator"

    inst_script "${_moddir}/leapp_debug_tools.sh" "/bin/leapp_debug_tools.sh"
    inst_script "${_moddir}/.profile" "/.profile"
    inst_script "${_moddir}/.shrc" "/.shrc"

    ## upgrade shell service
    #sysinit_wantsdir="${_initdir}${unitdir}/sysinit.target.wants"
    #mkdir -p "$sysinit_wantsdir"
    #inst_simple "${_moddir}/system-upgrade-shell.service" \
    #            "${unitdir}/system-upgrade-shell.service"
    #ln -sf "../system-upgrade-shell.service" "$sysinit_wantsdir"
}

