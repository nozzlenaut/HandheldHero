# RetroCommander

RetroCommander is my attempt at making handheld setup less annoying.

The idea is basically **Ninite for gaming handhelds**: plug in an Android handheld or point it at an SD card, pick what you actually want, and let the tool handle the boring part without turning setup into a 40-tab browser project.

This started because I have enough handhelds that setting the same stuff up over and over stopped being fun. I wanted one utility that could identify what I plugged in, show me what makes sense for that device, and install or stage the pieces I picked.

It is still early. I would rather have a smaller tool that does the useful stuff reliably than a giant one-click script that quietly makes a mess.

## What it does right now

### Android handhelds

RetroCommander can detect Android devices over ADB and offer Android-specific apps, emulators, tools, and frontends.

Current options include things like:

- RetroArch
- PPSSPP
- Dolphin
- DuckStation
- Azahar
- melonDS
- Flycast
- hakuX
- X360 Mobile
- Eden
- Citron Neo
- Winlator
- Moonlight
- Syncthing-Fork
- Steam / Steam Link
- Daijisho

The app scans what is already installed, marks those choices in the UI, and shows a running total for **selected / already installed / going to be installed**.

For normal GitHub-backed Android apps, **Obtainium is the update plan**. RetroCommander can install Obtainium and build an import JSON from the apps you selected instead of trying to reinvent a perfectly good updater.

Non-GitHub sources can still be checked separately where it makes sense.

### Modded Switch SD cards

RetroCommander can build or refresh a sane base Switch SD using current upstream releases.

The base currently handles:

- Atmosphere
- Hekate
- Nyx
- hbloader
- hbmenu
- fusee

Optional Switch tools currently include:

- Sphaira
- HB App Store
- MissionControl
- sys-clk
- Ultrahand Overlay
- NXThemesInstaller
- JKSV
- FTPD
- NX-Shell

Root-level packages are merged onto the SD instead of blindly replacing the whole card. Files that would be overwritten are backed up first.

RetroCommander also keeps a small local version manifest on the SD so later update checks can compare what it installed against current upstream versions instead of guessing.

### BIOS, firmware, and other local files

BIOS, Switch firmware, and local sigpatch packages all use the same basic picker:

- None
- Local ZIP
- Local folder

BIOS files can be copied to the expected locations for the selected handheld profile.

Switch firmware can be staged into a `firmware` folder for normal on-device use.

Local sigpatch packages are **staged only**. RetroCommander does not go hunting random mirrors for them or silently mix unknown patch packs into the base install.

## Current-version labels

One thing I wanted from the start was for the list to tell me what I am actually looking at.

RetroCommander pulls current source versions and shows them right in the UI, for example:

```text
PPSSPP (v1.20.4)
Sphaira homebrew menu (v1.0.7)
DuckStation (rolling 2026-09-12)
Base SD build/update (Hekate 6.5.3 / Nyx 1.9.3 / Atmosphere 1.11.2 / hbmenu 3.6.1)
```

Not every project publishes versions the same way. If upstream uses a rolling release or a date instead of a normal version number, RetroCommander shows that instead of making something up.

Version lookups are cached so opening the app does not hammer GitHub every single time. The **Check updates** button can force a fresh check.

## Dry Run

There is a **Dry Run** button because one-click setup tools should tell you what they are about to do before they start copying files everywhere.

The dry run lists things like:

- selected target and profile
- apps already installed
- apps that will actually be installed
- Switch base updates
- optional Switch tools
- BIOS / firmware / local package actions
- ROM-folder creation
- backup and verification steps

Then you can decide whether the plan looks sane before hitting **Run Setup**.

## Device profiles

The selected profile controls what is available in the UI. Things that do not make sense for that device get greyed out instead of just sitting there waiting to be clicked by accident.

Current profile groups include:

- Generic Android
- Retroid / Android
- AYN Odin / Android
- Anbernic Android
- TrimUI Brick / CrossMix / Stock
- TrimUI Brick / MinUI
- Generic Linux handheld SD
- Modded Switch SD

Device-specific detection and filtering will keep getting better as I actually test more hardware.

## A few intentional limits

There are a couple things RetroCommander intentionally does **not** try to be clever about.

- It does not download ROMs, games, keys, BIOS files, firmware, or other copyrighted files for you.
- It does not automatically grab random sigpatch packs from unofficial mirrors.
- It does not replace Obtainium for Android app updates when Obtainium already does the job well.
- It backs up things it is about to overwrite whenever practical.
- If a source/version cannot be identified honestly, the UI says so instead of inventing one.

The goal is convenience, not making a mystery box that happens to modify an SD card.

## Running it

Right now the main app is Python/Tkinter and is being packaged as a Windows executable.

The normal flow is:

1. Connect an Android handheld with USB debugging enabled **or** mount/select a handheld SD card.
2. Let RetroCommander detect the profile, or choose one manually.
3. Pick the apps/tools/setup pieces you want.
4. Check the install total and current versions.
5. Hit **Dry Run** if you want to see the exact plan.
6. Hit **Run Setup**.
7. Check the log if anything needed a manual tap or upstream did something weird.

## Project status

Very much a work in progress, but it is already useful enough that I wanted it out of the random-script-on-my-desktop stage.

Things I want to keep improving:

- more device profiles
- better installed-version detection
- better non-GitHub update checks
- cleaner Switch component/version detection
- RetroCommander self-update through GitHub releases
- eventually a proper release workflow so normal people do not need Python installed

If a feature makes setup easier and does not make the tool fragile, I am probably interested in it.

If it adds fifteen layers of magic just to save one click, probably not.

## Name

**RetroCommander** because apparently every handheld I own eventually becomes another tiny computer I need to administer.

Seems fair.
