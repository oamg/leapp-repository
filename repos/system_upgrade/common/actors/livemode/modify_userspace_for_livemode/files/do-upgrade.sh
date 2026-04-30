#!/bin/bash
# actually perform the upgrade, using UPGRADEBIN (set in /etc/conf.d)

warn() {
    echo "$@"
}

get_rhel_major_release() {
    local os_version
    os_version=$(grep -o '^VERSION="[0-9][0-9]*' /etc/os-release | grep -o '[0-9]*')
    [ -z "$os_version" ] && {
        # This should not happen as /etc/initrd-release is supposed to have API
        # stability, but check is better than broken system.
        warn "Cannot determine the major RHEL version."
        warn "The upgrade environment cannot be setup reliably."
        echo "Content of the /etc/os-release:"
        cat /etc/os-release
        exit 1
    }

    echo "$os_version"
}

RHEL_OS_MAJOR_RELEASE=$(get_rhel_major_release)
export RHEL_OS_MAJOR_RELEASE
export LEAPPBIN=/usr/bin/leapp
export LEAPPHOME=/root/tmp_leapp_py3
export LEAPP3_BIN=$LEAPPHOME/leapp3
export LEAPP_FAILED_FLAG_FILE="/root/tmp_leapp_py3/.leapp_upgrade_failed"

# this was initially a dracut script, hence $NEWROOT.
# the rootfs is mounted on /run/upgrade when booted with dmsquash-live
export NEWROOT=/run/upgrade

NSPAWN_OPTS="--capability=all --bind=/dev --bind=/dev/pts --bind=/proc --bind=/run/udev --bind=/run/lock"
[ -d /dev/mapper ] && NSPAWN_OPTS="$NSPAWN_OPTS --bind=/dev/mapper"
if [ "$RHEL_OS_MAJOR_RELEASE" == "8" ]; then
    # IPU 7 -> 8
    NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys --bind=/run/systemd"
else
    # IPU 8 -> 9
    # TODO(pstodulk, mreznik): Why --console=pipe? Is it ok? Discovered a weird
    # issue on IPU 8 -> 9 without that in our VMs
    NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys:/hostsys --console=pipe"
    # workaround to have the real host's root parameter in /proc/cmdline
    NSPAWN_OPTS="$NSPAWN_OPTS --bind-ro=/var/lib/leapp/.fakecmdline:/proc/cmdline"
    [ -e /sys/firmware/efi/efivars ] && NSPAWN_OPTS="$NSPAWN_OPTS --bind=/sys/firmware/efi/efivars"
fi
export NSPAWN_OPTS="$NSPAWN_OPTS --keep-unit --register=no --timezone=off --resolv-conf=off"



do_upgrade() {
    local args="" rv=0

    # Force selinux into permissive mode unless booted with 'enforcing=1'.
    # FIXME: THIS IS A BIG STUPID HAMMER AND WE SHOULD ACTUALLY SOLVE THE ROOT
    # PROBLEMS RATHER THAN JUST PAPERING OVER THE WHOLE THING. But this is what
    # Anaconda did, and upgrades don't seem to work otherwise, so...
    if [ -f /sys/fs/selinux/enforce ]; then
        enforce=$(< /sys/fs/selinux/enforce)
        ## FIXME: check enforcing bool in /proc/cmdline
        echo 0 > /sys/fs/selinux/enforce
    fi

    # and off we go...
    # NOTE: in case we would need to run leapp before pivot, we would need to
    #       specify where the root is, e.g. --root=/sysroot
    # TODO: update: systemd-nspawn

    # NOTE: We disable shell-check since we want to word-break NSPAWN_OPTS
    # shellcheck disable=SC2086
    /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "mount -a || : ; $LEAPPBIN upgrade --resume $args"
    rv=$?

    # NOTE: flush the cached content to disk to ensure everything is written
    sync

    ## TODO: implement "Break after LEAPP upgrade stop"

    if [ "$rv" -eq 0 ]; then
        # on aarch64 systems during el8 to el9 upgrades the swap is broken due to change in page size (64K to 4k)
        # adjust the page size before booting into the new system, as it is possible the swap is necessary for to boot
        # `arch` command is not available in the dracut shell, using uname -m instead
        # FIXME: check with LiveMode
        [ "$(uname -m)" = "aarch64" ] && [ "$RHEL_OS_MAJOR_RELEASE" = "9" ] && {
            cp -aS ".leapp_bp" $NEWROOT/etc/fstab /etc/fstab
            # swapon internally uses mkswap and both swapon and mkswap aren't available in dracut shell
            # as a workaround we can use the one from $NEWROOT in $NEWROOT/usr/sbin
            # for swapon to find mkswap we must temporarily adjust the PATH
            # NOTE: we want to continue the upgrade even when the swapon command fails as users can fix it
            # manually later. It's not a major blocker.
            PATH="$PATH:${NEWROOT}/usr/sbin/" swapon -af || echo >&2 "Error: Failed fixing the swap page size. Manual action is required after the upgrade."
            mv /etc/fstab.leapp_bp /etc/fstab
        }

        # NOTE:
        # mount everything from FSTAB before run of the leapp as mount inside
        # the container is not persistent and we need to have mounted /boot
        # all FSTAB partitions. As mount was working before, hopefully will
        # work now as well. Later this should be probably modified as we will
        # need to handle more stuff around storage at all.

        # NOTE: We disable shell-check since we want to word-break NSPAWN_OPTS
        # shellcheck disable=SC2086
        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "mount -a || : ; /usr/bin/python3 -B $LEAPP3_BIN upgrade --resume $args"
        rv=$?
    fi

    if [ "$rv" -ne 0 ]; then
        # set the upgrade failed flag to prevent the upgrade from running again
        # when the emergency shell exits and the upgrade.target is restarted
        local dirname
        dirname="$("$NEWROOT/bin/dirname" "$NEWROOT$LEAPP_FAILED_FLAG_FILE")"
        [ -d "$dirname" ] || mkdir "$dirname"

        echo >&2 "Creating file $NEWROOT$LEAPP_FAILED_FLAG_FILE"
        echo >&2 "Warning: Leapp upgrade failed and there is an issue blocking the upgrade."
        echo >&2 "Please file a support case with /var/log/leapp/leapp-upgrade.log attached."

        "$NEWROOT/bin/touch" "$NEWROOT$LEAPP_FAILED_FLAG_FILE"
    fi

    # NOTE: THIS SHOULD BE AGAIN PART OF LEAPP IDEALLY
    ## backup old product id certificates
    #chroot $NEWROOT /bin/sh -c 'mkdir /etc/pki/product_old; mv -f /etc/pki/product/*.pem /etc/pki/product_old/'

    ## install new product id certificates
    #chroot $NEWROOT /bin/sh -c 'mv -f /system-upgrade/*.pem /etc/pki/product/'

    # restore things twiddled by workarounds above. TODO: remove!
    if [ -f /sys/fs/selinux/enforce ]; then
        echo "$enforce" > /sys/fs/selinux/enforce
    fi
    return $rv
}

save_journal() {
    # Q: would it be possible that journal will not be flushed completely yet?
    echo "writing logs to disk"

    local logfile="/sysroot/tmp-leapp-upgrade.log"

    # Create logfile if it doesn't exist
    [ -n "$logfile" ] && true > $logfile

    # If file exists save the journal
    if [ -e $logfile ]; then
        # Add a separator
        echo "### LEAPP reboot ###" > $logfile

        # write out the logfile
        journalctl -a -m >> $logfile

        # We need to run the actual saving of leapp-upgrade.log in a container and mount everything before, to be
        # sure /var/log is mounted in case it is on a separate partition.
        local store_cmd="mount -a || : "
        local store_cmd="$store_cmd; cat /tmp-leapp-upgrade.log >> /var/log/leapp/leapp-upgrade.log"

        # NOTE: We disable shell-check since we want to word-break NSPAWN_OPTS
        # shellcheck disable=SC2086
        /usr/bin/systemd-nspawn $NSPAWN_OPTS -D "$NEWROOT" /usr/bin/bash -c "$store_cmd"

        rm -f $logfile
    fi
}


############################### MAIN #########################################

# workaround to replace the live root arg by the host's real root in
# /proc/cmdline that is read by /usr/lib/kernel/50-dracut.install
# during the kernel-core rpm postscript.
# the result is ro-bind-mounted over /proc/cmdline inside the container.
awk '{print $1}' /proc/cmdline \
    | xargs -I@ echo @ "$(cat "${NEWROOT}"/var/lib/leapp/.fakerootfs)" \
    > ${NEWROOT}/var/lib/leapp/.fakecmdline

##### do the upgrade #######
(
    # check if leapp previously failed in the initramfs, if it did return to the emergency shell
    [ -f "$NEWROOT$LEAPP_FAILED_FLAG_FILE" ] && {
        echo >&2 "Found file $NEWROOT$LEAPP_FAILED_FLAG_FILE"
        echo >&2 "Warning: Leapp failed on a previous execution and something might be blocking the upgrade."
        echo >&2 "Continuing with the upgrade anyway. Note that any subsequent error might be potentially misleading due to a previous failure."
        echo >&2 "A log file will be generated at $NEWROOT/var/log/leapp/leapp-upgrade.log."
        echo >&2 "In case of persisting failure, if possible, try to boot to the original system and file a support case with /var/log/leapp/leapp-upgrade.log attached."
    }

    [ ! -x "$NEWROOT$LEAPPBIN" ] && {
        warn "upgrade binary '$LEAPPBIN' missing!"
        exit 1
    }

    do_upgrade || exit $?
)
result=$?

##### save the data #####
save_journal

# NOTE: flush the cached content to disk to ensure everything is written
sync

# cleanup workarounds
/bin/rm -f ${NEWROOT}/var/lib/leapp/.fake{rootfs,cmdline} || true

# we cannot rely on reboot_system() from leapp.utils, since shutdown commands
# won't work within a container:
#"""
#System has not been booted with systemd as init system (PID 1). Can't operate.
#Failed to connect to bus: Host is down
#Failed to talk to init daemon: Host is down
#"""
if [ "$result" == "0" ]; then
    if [ -f "${NEWROOT}/.noreboot" ]; then
        echo "Reboot suppressed by ${NEWROOT}/.noreboot"
    else
        echo "Rebooting..."
        reboot
    fi
else
    echo >&2 "The upgrade container returned a non-zero exit code."
    exit $result
fi
