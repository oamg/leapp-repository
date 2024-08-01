# Writing an Actor for Leapp Upgrade

An **actor** is the core unit of execution in a Leapp upgrade workflow. If
something needs to be done during an upgrade, you likely need to create an
actor. A general overview of writing actors can be found in [How to Write an
Actor](TODO). This guide focuses on the specifics of writing actors for the
Leapp Repository.

## Formulate Your Requirements

The first step is to clearly define what you want to accomplish. Typically, the
process involves:

- Gathering system information
- Notifying the user about a change (via a ``Report``)
- Implementing the actual change during the upgrade

```{note}
### Case Study: Formulating Requirements

Suppose there's an application that changes behavior when upgrading from RHEL X
to RHEL Y. We need to adjust the configuration in `/etc/myapp/conf.ini`, but
only on specific systems. Say those using BIOS and are somehow *special*. For
the sake of an example, a system is considered *special* if the file
`/etc/special` exists.

Steps:
1. Detect if the system is *special* (i.e., check if `/etc/special` exists)
2. Detect if the system is running on BIOS
3. Notify the user about a potentially breaking change
4. Perform the configuration change
```

While these steps are interconnected, they may not all be implemented within a
single actor. It might be necessary to distribute them across different actors
in different phases of the upgrade process.

## Scout the Environment

Before implementing an actor, check if the necessary information is already
being collected by an existing actor or model in the repository. This can save
time and reduce redundancy.

```{note}
### Case Study: Scouting the Environment

To check if Leapp already provides information about the system running on
BIOS, you could search for "bios" in the Leapp Repository like

``grep -r "bios" repos/``

This search will lead you to the `FirmwareFacts` model, which contains exactly
the relevant information.
```

Many useful functions are also already available in libraries. Be sure to
review these before starting your implementation. For an overview consult 
[Leapp Upgrade Libraries](TODO)


## Determine Implementation Details

Once you’ve identified the reusable components, it’s time to start coding. You
should address the following questions during this stage:

- **What ``Model``s do I need to create?**

    Models are the primary means by which actors communicate and exchange
    information. Refer to [How to Create Models](TODO) for guidance.

- **Which actors will my actor interact with?**

- **Which phase should my actor belong to?**

    Refer to the [Phases Overview](TODO) for details on phase organization.


## Where to Place Your Actors

Deciding where to place your actor’s code depends on its scope:

- **Upgrade-specific code:** If your actor is relevant only for upgrading from
  RHEL X to RHEL Y, place it in `repos/system_upgrade/elXtoelY`.

- **Common code:** If your actor is applicable to all system upgrades, place it
  in `repos/system_upgrade/common`. This actor will be executed regardless of the
  upgrade path.

The same applies for models, library functions and other resources.


```{note} 
### Case Study: Actor Placement

You are creating two actors: `FirstActor` and `SecondActor`.

- `FirstActor` performs tasks applicable to all upgrades and should be placed
  in `repos/system_upgrade/common`.
- `SecondActor` is specific to the upgrade from RHEL 9 to RHEL 10, so it should
  be placed in `repos/system_upgrade/el9toel10`.
```
