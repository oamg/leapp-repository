# RFE: Leapp Preupgrade Analyzer for Older Release Packages

## Summary
Add a Leapp actor to detect and flag packages from older or different RHEL releases during the preupgrade phase, preventing system instability and unsupported configurations after upgrades.

## Problem Statement
Customers frequently upgrade from RHEL 7→8, 8→9, or 9→10 and retain packages from previous releases. For example:
- RHEL 8 systems with leftover RHEL 7 packages (`.el7`)
- RHEL 9 systems with RHEL 7 or RHEL 8 packages (`.el7`, `.el8`)
- RHEL 10 systems with packages from any older release (`.el6`, `.el7`, `.el8`, `.el9`)

These mixed-release packages cause:
- System instability
- Broken upgrades
- Unsupported "grey state" configurations
- Application failures due to incompatible dependencies

Red Hat does not support systems with packages from different major RHEL releases (e.g., RHEL X packages on RHEL Y systems where X ≠ Y).

## Proposed Solution
Implement a Leapp actor that:

1. **Detects packages from other releases** based on the current OS version
2. **Flags them as an inhibitor** in the Leapp preupgrade report
3. **Provides actionable guidance** to customers on remediation

### Detection Logic

For each RHEL version, check for packages from older releases:

**RHEL 7:**
```bash
rpm -qa | grep -i el6
```

**RHEL 8:**
```bash
rpm -qa | grep -E '\.el(6|7)\b'
```

**RHEL 9:**
```bash
rpm -qa | grep -E '\.el(6|7|8)\b'
```

**RHEL 10 (and future releases):**
```bash
rpm -qa | grep -E '\.el(6|7|8|9)\b'
```

### Inhibitor Message

When older release packages are detected:

```
WARNING: Packages from different RHEL releases detected

The system contains the following packages from older RHEL releases:
[list of packages]

These packages may cause system instability, upgrade failures, or unsupported configurations.

Recommended actions:
1. Remove these packages before proceeding with the upgrade
2. Contact Red Hat Support for assistance with package migration
3. Contact the application vendor/ISV for updated packages compatible with the target RHEL version

Red Hat does not support systems with packages from different major RHEL releases.
Proceeding with the upgrade while these packages are installed may result in an unsupported system state.
```

## Benefits

1. **Prevents unsupported configurations** - Catches mixed-release packages before upgrade
2. **Reduces support escalations** - Proactively identifies issues customers would encounter post-upgrade
3. **Improves upgrade success rate** - Ensures clean upgrade paths
4. **Provides clear guidance** - Customers know exactly what needs remediation

## Scope

- **Target RHEL versions:** RHEL 9, RHEL 10, and all future releases
- **Backward compatibility:** Can be backported to RHEL 7→8 and 8→9 upgrade paths if needed
- **Exclusions:** Should not flag Leapp-specific packages (e.g., `el7toel8` packages used by Leapp itself)

## Success Criteria

When implemented, this feature will:
- Detect all packages with release tags different from the current OS release
- Display them as inhibitors in the Leapp preupgrade report
- Provide clear remediation guidance
- Prevent systems from entering unsupported states due to mixed-release packages

## Related Context

This addresses a common customer pain point observed in support cases where post-upgrade systems have degraded functionality or unsupported configurations due to leftover packages from previous RHEL releases.

---

**Note:** This RFE focuses on RHEL 9 and later releases. The detection logic can be adapted for earlier RHEL versions if the Leapp team determines it's valuable for those upgrade paths as well.
