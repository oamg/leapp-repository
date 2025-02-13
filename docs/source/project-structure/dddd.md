# device_driver_deprecation_data.json (AKA DDDD or HW data)
The `device_driver_deprecation_data.json` file specifies the state of devices and drivers (maintained, unmaintained, ...) in particular major versions of RHEL. During the upgrade, file is used to check whether detected HW & drivers are:
- still available & maintained in the target system
- available but not maintained anymore (high risk, but upgrade is possible)
- dropped from the system entirely (inhibit the upgrade)

```{note}
This data is often referred to as HW data, HW deprecation data, or in case of leapp-repository also DDDD.json file as the actual name is too long.
```

## Why is DDDD necessary for the upgrade?
It's common that number of drivers and HW are not fully supported on the next major version of RHEL. They can be either removed completely or just not maintained anymore but it's important to check whether the upgrade could negatively affect the machine anyway.

Imagine that you have an old piece of HW that you heavily depend on and the upgraded system will not understand it at all - e.g. your old network card can be dead and you will not be able to connect to the machine anymore. Or that the new system cannot be actually executed or installed on your HW at all (there are such cases). To be able to do such checks leapp needs to have information about what is supported, available, unmaintained, or unavailable on particular systems. And that's the content of the discussed file.

## Terminology
Note that regarding devices and drivers you can see following terms:

- enabled and fully **maintained**
- **deprecated**
- **unmaintained**
- **disabled**
- **removed**

In the upgrade project we operate usually just with:
- maintained
- unmaintained → available but not maintained. In the terms of the upgrade process, is equal to deprecated, even when it's not exactly the same
- removed

% ## How is DDDD used during the upgrade?
% TBD.
