#!/bin/bash
###############################################################################
stage() {
    echo '###############################################################################'
    printf "%*s\n" $(((80 - ${#1}) / 2)) "$1"
    echo '###############################################################################'
}

get_kernel_version() {
    rpm -qa | grep kernel-modules | cut -d- -f3- | sort | tail -n 1
}

dracut_install_modules()
{
    stage "Installing leapp dracut modules"
    modir="/usr/lib/dracut/modules.d/";
    pushd /dracut
    for folder in $(find . -maxdepth 1 -type d);
    do
        /bin/cp -fa $folder $modir;
    done;
    stage "Fixing permissions on leapp dracut modules"
    chown -R "root:root" "$modir";
    restorecon -r "$modir"
    popd
}


build() {
    dracut_install_modules

    stage "Setting up artifacts folder"
    rm -rf /artifacts
    mkdir -p /artifacts

    DRACUT_CONF=${LEAPP_DRACUT_CONF:-/dev/null}
    DRACUT_CONF_DIR=${LEAPP_DRACUT_CONF:-/var/empty}

    DRACUT_LVMCONF_ARG="--nolvmconf"
    if [[ ! -z LEAPP_DRACUT_LVMCONF ]]; then
        DRACUT_LVMCONF_ARG="--lvmconf"
    fi
    DRACUT_MDADMCONF_ARG="--nomdadmconf"
    if [[ ! -z LEAPP_DRACUT_MDADMCONF ]]; then
        # include local /etc/mdadm.conf
        DRACUT_MDADMCONF_ARG="--mdadmconf"
    fi

    KERNEL_VERSION=$LEAPP_KERNEL_VERSION
    if [[ -z $KERNEL_VERSION ]]; then
        KERNEL_VERSION=$(get_kernel_version)
    fi

    KERNEL_ARCH='x86_64'
    if [[ ! -z $LEAPP_KERNEL_ARCH ]]; then
        KERNEL_ARCH=$LEAPP_KERNEL_ARCH
    fi

    DRACUT_MODULES_ADD=""
    if [[ -z $LEAPP_ADD_DRACUT_MODULES ]]; then
        echo 'ERROR: No dracut modules to add'
        exit 1;
    else
        DRACUT_MODULES_ADD=$(echo "--add $LEAPP_ADD_DRACUT_MODULES" | sed 's/,/ --add /g')
    fi

    pushd /artifacts
    \cp /lib/modules/$KERNEL_VERSION/vmlinuz vmlinuz-upgrade.$KERNEL_ARCH

    stage "Building initram disk for kernel: $KERNEL_VERSION"
    \dracut \
        -vvvv \
        --force \
        --conf $DRACUT_CONF \
        --confdir $DRACUT_CONF_DIR \
        --install systemd-nspawn \
        $DRACUT_MODULES_ADD \
        $DRACUT_MDADMCONF_ARG \
        $DRACUT_LVMCONF_ARG \
        --no-hostonly \
        --kver $KERNEL_VERSION \
        --kernel-image vmlinuz-upgrade.$KERNEL_ARCH \
        initramfs-upgrade.$KERNEL_ARCH.img
    popd
    stage "Building initram disk for kernel: $KERNEL_VERSION finished"
}

build
