# repomap.json - Repomapping
Repomapping is mapping between repositories on the source system to repositories on the target system. `repomap.json` is a file that contains information about how repositories should be mapped.

## Why does leapp need repomapping?
The RHEL repository ecosystem is vast and complex. There are different repositories for different architectures (x86_64, s390x, ...), channels (ga, els, e4s, ...), cloud providers (azure, aws, ...). There is no standard naming scheme for all repository IDs (repoids) used across the whole portfolio and you can find that especially in case of clouds repoids are changed even during one RHEL X lifecycle. RepoIDs sometimes differ across RHEL major versions only in version number, e.g. `rhel-9-for-aarch64-baseos-rpms` maps to `rhel-10-for-aarch64-baseos-rpms`, but sometimes the entire repoid is different. Some repositories also map to multiple repositories for example the RHEL 7 base repo maps to BaseOS and Appstream on RHEL8.

It would be impossible for leapp to guess which repositories should be enabled on the target system based only on the repositories present on the source system. This information is provided to leapp in the `repomap.json` file which leapp then parses and processes to determine the correct target repositories.

## repomap.json
The `repomap.json` file contains information about repomapping, more precisely it consists of 2 main sections, *mapping* and *repositories*. The structure of the contents is defined by a well documented JSON schema which can be found in the [oamg/schema-test repository](https://github.com/oamg/schema-test) along with schemas for other Leapp data files.

Briefly put, the mapping is an array that contains the individual mappings between repositories between RHEL major versions, however repositories in this case are not referenced by repoids, but PES IDs.  A PES ID refers to a set of repositories which represent alternative variants of one repository. E.g. BaseOS has a little different repoid for every architecture, channel, ... The repositories part is an array of mappings between PES IDs and an array of the alternative repoids.

##  How leapp determines the target repositories?
Target repoisitories are mapped based on:
- the repositories enabled on the source system via RHSM
- the repositories from which the installed RPMs (signed by RH) originate
  - Note that RPMs can also be installed from virtual repositories, custom repositories, or from a local file, so we do not always have helpful information about the origin of the installed content (see below)

The mapping process is as follows:
1. Each repository (repoid) is looked up in the `repomap.json` file, if it's present the corresponding PES ID (pesid) is retrieved. If it's not present:
    - in case the repository is enabled on the source system, there is no mapping we could do, therefore such repositories are skipped as repositories unknown to the upgrade project
    - in case the repository is the origin of an installed RPM, the potential pesid is obtained from `pes-events.json` file (TODO link: see other leapp data files); if a PES event for such an RPM is discovered in PES data, the attached pesid is used

2. The source pesid is mapped to the target pesid(s) and based on other attributes (such as expected target channel, rhui, architecture, ...) the expected equivalent target repoid (one repoid per each defined target pesid) is picked.

### Example
1. A repository with repoid `rhel-7-server-rpms` is discovered on the source system:
   -  it is defined for x86_64 architecture, ga channel, and it's not rhui
2.  in the *mapping* section of `repomap.json`, this repoid is found under pesid `rhel7-base` , which is mapped to: `rhel8-AppStream` and `rhel8-BaseOS` pesids
4. check what repositories are defined under the `rhel8-AppStream` and `rhel8-BaseOS` pesids in the *repositories* section of `repomap.json` and find the most suitable repoids for the target. Those are:
   - `rhel-8-for-x86_64-appstream-rpms` (rhel8-Appstream)
   - `rhel-8-for-x86_64-baseos-rpms` (rhel8-BaseOS)
