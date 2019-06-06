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
    for folder in $(find . -name "*sys-upgrade*");
    do
        /bin/cp -fa $folder $modir;
    done;
    stage "Fixing permissions on leapp dracut modules"
    chown -R "root:root" "$modir";
    restorecon -r "$modir"
}


build() {
    dracut_install_modules

    stage "Setting up artifacts folder"
    rm -rf /artifacts
    mkdir -p /artifacts

    pushd /artifacts
    KERNEL_VERSION=$(get_kernel_version)
    \cp /lib/modules/$KERNEL_VERSION/vmlinuz vmlinuz-upgrade.x86_64
    stage "Building initram disk for kernel: $KERNEL_VERSION"
    \dracut \
        -vvvv \
        --conf /dev/null \
        --confdir /var/empty \
        --force \
        --add sys-upgrade \
        --install systemd-nspawn \
        --no-hostonly \
        --nolvmconf \
        --nomdadmconf \
        --force \
        --verbose \
        --kver $KERNEL_VERSION \
        --kernel-image vmlinuz-upgrade.x86_64 \
        initramfs-upgrade.x86_64.img
    popd
    stage "Building initram disk for kernel: $KERNEL_VERSION finished"
}

build
