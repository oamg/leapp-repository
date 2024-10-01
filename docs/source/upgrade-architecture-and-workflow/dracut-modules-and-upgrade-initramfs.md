# Leapp dracut modules and upgrade initramfs
The actual upgrade of RPMs in leapp happens in an upgrade initramfs. In RHEL
[dracut](https://github.com/dracutdevs/dracut) is used for building initramfs
and it's also used by leapp.

```{note}
This document documents the traditional leapp initramfs approach, not the
experimental livemode initramfs, although some of the information holds true
for livemode too.
```

The primary reasons for using an initramfs are that it is isolated and in our
full control. We can decide what kernel/dracut modules, scripts, etc. are
included and also allow actors to influence that using messages. We can also
decide what runs and doesn't run there. This is important to make sure no
other services interfere with the upgrade.

Systemd is used inside the upgrade initramfs to start leapp's `upgrade.service`
systemd service at the appropriate time when we are sure all the required setup
has completed. Currently the service requires `basic.target` and
`sysroot.mount`.

The actual DNF transaction installs the packages downloaded in the
pre-initramfs part of the upgrade via leapp's DNF plugin. The target userspace
is mounted by the plugin and the upgrade transaction is executed. Applications
and third-party applications are also upgraded in the initramfs.

The final step in the initramfs is preparation for booting into the target
system. This includes tasks such as creating the leapp-resume.service, target
initramfs generation, selinux relabeling, enabling/disabling systemd services...

## Preparing the generation of initramfs
The `commonleappdracutmodules` actor is responsible for the preparation of
initramfs generation. It produces tasks with information about which RPMs
(dracut, mdadm, lvm2, ...) necessary for building the initramfs need to be
installed and which dracut and kernel modules need to be included. At minimum
the following 2 modules are included:
- `85sys-upgrade-redhat` - mounts the `/usr` filesystem inside initramfs and
runs the actual upgrade
- `90sys-upgrade` - contains the upgrade.service and upgrade.target, the
service then runs upgrade scripts from `85sys-upgrade-redhat`

### Including custom dracut and kernel modules
Actors and custom actors can produce messages to include custom dracut
modules as well as kernel modules in the upgrade initramfs. See [TBD
link](templates) for examples on how to write such actors.

TBD - add/link the doc to the relevant models here

## Generating the initramfs
The initramfs is built by the `upgradeinitramfsgenerator` actor. It collects
and installs the required RPMs, collects and includes kernel and dracut modules
and copies required files (e.g. the initramfs generator script) from host to
the target userspace container. Generates the initramfs using `dracut` and
copies it to `/boot`.

## Network in initramfs
Currently networking support in the initramfs is experimental. See [TDB link
LEAPP_DEVEL_INITRAM_NETWORK]() for more information.

## Debugging inside initramfs
See [TDB link]() for detailed information about initramfs debugging.
