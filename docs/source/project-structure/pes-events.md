# pes-events.json - PES data
PES data contain information about evolution of RPMs (binary packages) between versions of RHEL systems.

The data is structured as an array of *events*. An example event:
```json
{
  "action": 1, // type of the event (removal in this case): present, removal, split, merge, ...
    "architectures": [ // which architectures it affects
      "aarch64",
      "ppc64le",
      "s390x",
      "x86_64"
    ],
  "id": 8, // event ID
  "in_packageset": { // packages before the event
    "package": [
      {
        "modulestreams": [
          null
        ],
        "name": "empathy",
        "repository": "rhel7-base" // PES ID (pesid)
      }
    ],
    "set_id": 12
  },
  "initial_release": { // initial release of the package(s)
    "major_version": 7,
      "minor_version": 7,
      "os_name": "RHEL"
  },
  "modulestream_maps": [], // mapping between modulestreams (if packages are modularized)
  "out_packageset": null, // packages after the event (null in this case as it's a removal event)
  "release": { // the release on which the event happened (note that's its MAJOR.MINOR)
    "major_version": 8,
    "minor_version": 0,
    "os_name": "RHEL"
  }
}
```

## Why is PES data necessary for the upgrade?
We can explain this by comparing RHEL upgrades to Fedora upgrades. Fedora upgrade process, on a basic level, replaces the system repository for the new one and basically performs a distro-sync. Pretty straightforward.
One might be wondering why the same isn't done in RHEL. There are several problems with that:
- Fedora release cycle is every 6 months, new major version of RHEL is introduced each 3 years. That means 6 Fedora versions.
  - In the past, the longest jump has been between RHEL 7 and RHEL 8. It has been 10 Fedora versions! (Fedora 19 → 29),
- SPEC files in Fedora keep compatibility across 3 Fedora releases only!
  - a lot of things that have been present in SPEC files are just dropped in the 3rd Fedora release - *especially Provides & Obsoletes*!
- SPEC files usually do not reflect changes in packages on more granular level. It's gotten better since the introduction of rich dependencies. However, they are not used always "correctly":
  - Imagine you have a package pkgA. In the next system you split some functionality to subpkg pkgB and do not require it to be installed automatically with pkgA - not setting recommendation or weak dependency. After upgrading the system, you will end up with just pkgA and you will possibly realize that the application/SW does not work as expected, becaused you are missing pkgB. By the way, this is called a "split" event in PES. As when upgrading RHEL systems, you want to have both installed by default. If the user realizes they do not need it, they can always remove it later.
- Fedora has basically just one repository, while RHEL has *many* and packages can be moved around them. DNF modules and RHUI bring even more complexity to this already complex ecosystem.
  - PES data is in synergy with {doc}`repomap.json<repomap>`!

PES data is used to provide supporting instructions to DNF (or libsolver) that tell it what packages should be removed and installed and we leave libsolver to do the rest of the work for packages which are let's say undefined (no entry in PES).

## How is PES data processed and used during the upgrade?
TBD
