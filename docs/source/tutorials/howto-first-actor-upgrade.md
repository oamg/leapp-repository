# How to write an Actor for Leapp Upgrade

An **actor** is the core unit of execution in a Leapp upgrade workflow. If
something needs to be done during an upgrade, you likely need to create an
actor. We advise to read the {external:doc}`general tutorial on writing actors
for the Leapp framework<tutorials/first-actor>` first, it will help
understanding the concept. This guide helps you to create your actors
*specifically* for the **In-Place Upgrade (IPU)** process between major
versions of RHEL systems (or RHEL-like systems if relevant).

```{note}
When speaking about e.g. IPU 8 -> 9, it means an In-Place Upgrade from RHEL 8
to RHEL 9 (or RHEL-like systems if relevant).
```

## Create the first actor for IPU

This is a small baby step in nutshell similar to the general guide, but start
with something small this time.
To simply create an actor for upgrades, you need to do basically this:

1. Go to the `actors` directory of a leapp repository based on what IPU you
   want to deal with (e.g. `system_upgrade/el8toel9/actors` for IPU 8 -> 9).
2. Create your initial actor for the **[IPUWorkflow](https://github.com/oamg/leapp-repository/blob/main/repos/system_upgrade/common/workflows/inplace_upgrade.py)**
   workflow and specific workflow's phase
   To do that you have to just specify correct tags for the actor:
   * `IPUWorkflowTag` - specifies that actor is connected to the
     **IPUWorkflow** workflow.
   * a *phase tag* - specifies during which phase of **IPUWorkflow**
     the actor will be executed.

   So the simple snactor command could be like this:
   ```shell
   snactor new-actor MyNewActorName --tag IPUWorkflowTag --tag <PhaseTag>
   ```
   Let's say we will want to create an actor that will scan the source system,
   so we will use `FactsPhaseTag` to execute it during first defined phase.
   That would result in an actor like this:
   ```python
   from leapp.actors import Actor
   from leapp.tags import IPUWorkflowTag, FactsPhaseTag


   class MyNewActorName(Actor):
       """
       No documentation has been provided for the my_new_actor_name actor.
       """

       name = 'my_new_actor_name'
       consumes = ()
       produces = ()
       tags = (IPUWorkflowTag, FactsPhaseTag)

       def process(self):
           pass
   ```
   The `process` method is called by leapp when executing the actor.

   ```{note}
   In this guide we keep the code in the `process` method to keep examples simple.
   In real life we strongly suggest to follow the best practices in this project
   and put all your code into actor's library. This will usually make your life
   easier, especially when trying to write unit-tests for actors.
   As an example, see the [rpm_scanner](https://github.com/oamg/leapp-repository/tree/main/repos/system_upgrade/common/actors/rpmscanner)
   actor.
   ```

Next to number of existing actors, we suggest you to examine
{doc}`templates</tutorials/templates/index>` we prepared for some specific
use-cases that could help you with some tasks.

### Most common phases for actors
Unless you need to do something special most likely you will want to use usually
these tags for **IPUWorkflow**'s phases:
* `FactsPhaseTag` - scan the system and produce facts for other actors
* `ChecksPhaseTag` - evaluate the system state based on collected facts
  and plan what to do next or create reports for users - which includes possible
  stop of the upgrade process (e.g. when the HW is not possible to use on the target system).
* `ApplicationsPhaseTag` - For actors modyfiying the upgraded system (after the
  RPM upgrade transaction is finished successfully). Alternatively, use
  `ThirdPartyApplicationsPhaseTag` for custom or third-party applications.


## Formulate Your Requirements

The first step is to clearly define what you want to accomplish. Typically, the
process involves:

- Gathering system information
- Notifying the user about a change or inhibit (stop) the upgrade (via a ``Report``)
- Implementing the actual change during the upgrade

```{note}
### Case Study: Formulating Requirements

Suppose there's an application that changes behavior when upgrading from RHEL X
to RHEL Y. We need to adjust the configuration in `/etc/myapp/conf.ini`, but
only on specific systems. Say those using BIOS and somehow else *special*. For
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
{doc}`/libraries-and-api`.


## Determine Implementation Details

Once you’ve identified the reusable components, it’s time to start coding. You
should address the following questions during this stage:

- **What ``Model``s do I need to create?**

    Models are the primary means by which actors communicate and exchange
    information. Refer to {external:doc}`tutorials/messaging` for guidance.

- **Which actors will my actor interact with?**

- **Which phase should my actor belong to?**

    Refer to the {doc}`/upgrade-architecture-and-workflow/phases-overview` for details on phase organization.


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
