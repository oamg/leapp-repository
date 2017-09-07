#!/bin/bash
# actually perform the upgrade, using UPGRADEBIN (set in /etc/conf.d)

export DRACUT_SYSTEMD=1
if [ -f /dracut-state.sh ]; then
    . /dracut-state.sh 2>/dev/null
fi
type getarg >/dev/null 2>&1 || . /lib/dracut-lib.sh

export LEAPPBIN=/usr/bin/leapp

do_upgrade() {
    local args="" rv=0
    #FIXME: set here params we would like to possible use...
    #getargbool 0 rd.upgrade.test && args="$args --testing"
    #getargbool 0 rd.upgrade.verbose && args="$args --verbose"
    getargbool 0 rd.upgrade.debug && args="$args --debug"

    # Force selinux into permissive mode unless booted with 'enforcing=1'.
    # FIXME: THIS IS A BIG STUPID HAMMER AND WE SHOULD ACTUALLY SOLVE THE ROOT
    # PROBLEMS RATHER THAN JUST PAPERING OVER THE WHOLE THING. But this is what
    # Anaconda did, and upgrades don't seem to work otherwise, so...
    if [ -f /sys/fs/selinux/enforce ]; then
        enforce=$(< /sys/fs/selinux/enforce)
        getargbool 0 enforcing || echo 0 > /sys/fs/selinux/enforce
    fi

    # Incase we have the LVM command available try make it activate all partitions
    if command -v lvm 2>/dev/null 1>/dev/null; then
        lvm vgchange -a y
    fi

    # and off we go...
    # NOTE: in case we would need to run leapp before pivot, we would need to
    #       specify where the root is, e.g. --root=/sysroot
    # TODO: update: systemd-nspawn
    $NEWROOT/bin/systemd-nspawn --capability=all --bind=/sys --bind=/dev --bind=/proc --keep-unit --register=no -D $NEWROOT $LEAPPBIN upgrade --resume $args
    rv=$?

    # NOTE: THIS SHOULD BE AGAIN PART OF LEAPP IDEALLY
    ## backup old product id certificates
    #chroot $NEWROOT /bin/sh -c 'mkdir /etc/pki/product_old; mv -f /etc/pki/product/*.pem /etc/pki/product_old/'

    ## install new product id certificates
    #chroot $NEWROOT /bin/sh -c 'mv -f /system-upgrade/*.pem /etc/pki/product/'

    # restore things twiddled by workarounds above. TODO: remove!
    if [ -f /sys/fs/selinux/enforce ]; then
        echo $enforce > /sys/fs/selinux/enforce
    fi
    return $rv
}

save_journal() {
    # Q: would it be possible that journal will not be flushed completely yet?
    echo "writing logs to disk and rebooting"

    local logfile="$NEWROOT/var/log/upgrade.log"

    # back up old logfile, if present
    [ -e $logfile ] && rm -rf $logfile.old && mv $logfile $logfile.old

    # write out the logfile
    journalctl -a -m > $logfile
}


############################### MAIN #########################################
# get current mount options of $NEWROOT
# FIXME: obviously this is still wrong solution, but resolve that later, OK?
old_opts=""
declare mount_id parent_id major_minor root mount_point options rest
while read -r mount_id parent_id major_minor root mount_point options \
        rest ; do
    if [ "$mount_point" = "$NEWROOT" ]; then
        old_opts="$options"
        break
    fi
done < /proc/self/mountinfo
if [ -z "$old_opts" ]; then
    old_opts="defaults,ro"
fi

# enable read/write $NEWROOT
mount -o "remount,rw" $NEWROOT

##### do the upgrade #######
(
    [ ! -x "$NEWROOT$LEAPPBIN" ] && {
        warn "upgrade binary '$LEAPPBIN' missing!"
        exit 1
    }

    do_upgrade || exit $?
)
result=$?

##### safe the data and remount $NEWROOT as it was previously mounted #####
save_journal
mount -o "remount,$old_opts" $NEWROOT
exit $result

