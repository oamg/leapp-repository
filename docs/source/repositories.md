# Repositories Overview

The **Leapp** project uses a modular repository structure in `repos/system_upgrade` to support multiple upgrade paths
and shared functionality across these paths.
Each repository contains actors, models, workflows,
and supporting code for a specific upgrade path or common functionality.

## High-Level Structure
```
repos/
├── system_upgrade/
│   ├── common/
│   ├── el7toel8/
│   ├── el8toel9/
│   └── el9toel10
│   └── ...
```
## Main Repositories

- **`repos/system_upgrade/common/`**: Contains shared code that applies to all in-place upgrades,
regardless of the specific source and target versions.
- **`repos/system_upgrade/elXtoelY/`**: Contains code specific to concrete upgrade path.

## How to Determine Where to Place a New Entity?

When developing a new actor, model, or library, use the following guidelines to determine where to place it:

- **Determine the Upgrade Path**:
  - Is the functionality specific to a certain upgrade path?
  - If your entity is related to upgrading specific paths, place it in repos/system_upgrade/elXtoelY/.

- **Is It Generic or Reusable Across Upgrade Paths?**:
  - If the entity is not specific to any one upgrade path and can be reused across multiple upgrades 
(e.g., system checks, disk space validation, network settings), place it in the repos/system_upgrade/common/ repository.

- **Classify by Type**:
  - Actor: If you’re creating an actor, 
place it in the actors/ directory of the appropriate repository (version-specific or common).
  - Model: If it’s a data structure shared between actors, place it in the models/ directory of the relevant repository.
  - Library: Utility functions that support actors go in the libraries/ directory.

- **Use Existing Tags When Appropriate**:
   - When creating new actors, consider using existing tags (such as PreUpgrade, PostUpgrade, etc.)
to categorize when the actor should be executed during the upgrade.

Using changes in the Leapp repositories to perform an in-place upgrade involves modifying or adding new actors, models, 
and workflows, building the modified repository, and using the Leapp tool to execute the upgrade. After integrating your changes, the upgrade process runs seamlessly with the customizations you've added,
ensuring the system is upgraded according to your specifications.