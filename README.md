# Home Assistant Configuration

This is a basic configuration I use with the Home Assistant home automation platform.

## Basic goals

* Make day-to-day tasks easier -- if I find myself doing a group of actions repeatedly, I want to just take one action and have the others "automagically" happen. An example of this is dimming the lights and turning off loud fans once a movie starts.

* Stay informed throughout my day. If I have tasks to do, I want to be constantly reminded they need to be done until they are complete. If something is happening (for example, pizza is about to be delivered), I want to know about it.

* Save money and effort by automatically reducing energy usage when I'm not home. Things like turning off the lights and fans once nobody is home. This is related to the first point above.

I think of this as like having a "secretary" of sorts managing the house. Not all these goals are there yet, but they're what I strive for.

## Hardware

* I'm running Hass.io on a Raspberry Pi 3B

* I also have a Netgear NAS, which keeps local + cloud backups of all my files and doubles as a Plex media server

* I use Harmony to manage turning TVs on and off

* My lights are controlled with Hue

* Fans (and more lights) are controlled with WeMo

* I have Google Chromecasts hooked up to "dumb" TVs

* I have a Tesla Model 3 which is hooked into my smart home

* I have a Ring Doorbell

* Things are hooked into IFTTT -- due to the nature of IFTTT, however, you're only getting "half the story" by looking at this repo, as it were

## Organization

I'm in the process of reorganizing these files. Currently, things are split like so:

* `configuration.yaml` is the "main" file that gets executed to kick everything off.

* `hass.yaml` gets loaded by `configuration.yaml`, which in turn loads each integration inside the `integrations` folder. This groups together all sensors, all climate controllers, etc.

* Certain integrations have a lot of entities associated with them, for example `binary_sensor`. For this, there's a separate `entities` folder, which keeps track of each individual entity.

* There's also the `automations` folder, which keeps track of all my automations. Generally, my automations follow the ["observer pattern"](https://sourcemaking.com/design_patterns/observer), where there's a "subject" which handles the actual logic dictating state changes. The subject fires an event, which "observer" automations listen to. This means everything is event-driven -- if I want to change how things get triggered, rather than updating 50 files, I just need to update the subject that actually fires the event.
