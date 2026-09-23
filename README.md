# HandheldHero

HandheldHero is my attempt at making handheld setup less annoying.

The easiest description is basically **Ninite-ish setup for gaming handhelds**: plug in an Android handheld or point it at an SD card, check the stuff you actually want, see what is already there, and let one tool handle the boring part.

I own enough little computers at this point that setting up the same emulators, folders, BIOS paths, frontends, homebrew, and update stuff over and over stopped being fun. HandheldHero came out of wanting one utility that could do that without becoming a giant black-box script that touches everything and explains nothing.

The rule for this project is pretty simple: **if it is going to modify a handheld or SD card, it should tell you what it is doing first and be boring about it.**

Current version: **v0.6**

## What it does right now

### Android handhelds

HandheldHero can detect Android devices over ADB, pick a useful device profile, scan what is already installed, and offer Android-specific apps, emulators, tools, and frontends.

Current options include:

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

The checklist shows source/current versions where the upstream project exposes something useful. Once a device is connected it also marks installed apps and keeps a live total for **selected / already installed / will install**.

For normal GitHub-backed Android apps, **Obtainium is the update plan**. HandheldHero can install Obtainium and build an import JSON containing the apps you selected. I do not see much value in writing a second worse version of Obtainium just so this project can say it has an updater.

Play Store apps stay Play Store apps. Non-GitHub sources can be checked separately where it makes sense.

### Modded Switch SD cards

HandheldHero can build or refresh a sane base Switch SD using current upstream releases.

The base handles:

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

Root-level packages are merged onto the SD instead of replacing the whole card. Anything HandheldHero is about to overwrite gets backed up when practical.

The app also keeps a small version manifest on the SD. That gives **Check updates** something real to compare against later instead of trying to reverse-engineer versions from random files every time.

### BIOS, firmware, and local packages

BIOS, Switch firmware, and local sigpatch packages all use the same picker:

- None
- Local ZIP
- Local folder

BIOS files are copied to the expected locations for the selected profile.

Switch firmware is staged into a `firmware` folder for normal on-device use.

Local sigpatch packages are **staged only**. HandheldHero does not go hunting mystery mirrors or silently mix some random patch ZIP into Atmosphere.

It also does **not** download ROMs, games, keys, BIOS files, or firmware for you. I want a useful setup tool, not a legal-landmine button.

## Current-version labels

I wanted the list to tell me what I am actually looking at instead of just showing a name and making me wonder whether it is from three years ago.

Examples look like this:

```text
PPSSPP (v1.20.4)
Sphaira homebrew menu (v1.0.7)
DuckStation (rolling 2026-09-12)
Base SD build/update (Hekate 6.5.3 / Nyx 1.9.3 / Atmosphere 1.11.2 / hbmenu 3.6.1)
```

Not every project publishes versions the same way. If upstream uses a rolling release, date, build number, or something else weird, HandheldHero shows that honestly instead of making up a nicer-looking version number.

Version lookups are cached for a few hours so opening the app does not beat GitHub over the head with API requests. **Check updates** forces a fresh check.

## Dry Run

There is a **Dry Run** button because a one-click setup tool should tell you what the click is going to do.

Dry Run shows things like:

- selected target and profile
- apps already installed
- apps that will actually be installed
- Switch base updates
- optional Switch tools
- BIOS / firmware / local-package actions
- ROM-folder creation
- backup and verification steps

Nothing is written during Dry Run.

## Device profiles

Profiles control what is available in the UI. Stuff that makes no sense for the selected device gets greyed out instead of being left clickable and failing later.

Current profile groups:

- Generic Android
- Retroid / Android
- AYN Odin / Android
- Anbernic Android
- TrimUI Brick / CrossMix / Stock
- TrimUI Brick / MinUI
- Generic Linux handheld SD
- Modded Switch SD

The profile list is intentionally not 400 devices long. I would rather keep a few useful groups and add device-specific behavior where it actually matters.

## Running from source

HandheldHero is currently a Windows-first Python/Tkinter app.

You need Python 3.12+ and ADB/Android Platform Tools if you want Android detection/install support.

```powershell
python handheld_hero.py
```

Tkinter ships with normal Windows Python installs, so there is no giant `requirements.txt` full of UI packages.

## Building the Windows EXE

The app can be packaged with PyInstaller:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name HandheldHero handheld_hero.py
```

The repo also includes a GitHub Actions workflow that builds the Windows EXE **only when manually requested or when a `v*` tag is pushed**. I am intentionally not generating a giant artifact on every commit.

## Normal use

1. Connect an Android handheld with USB debugging enabled **or** mount/select a handheld SD card.
2. Let HandheldHero detect the profile, or pick one manually.
3. Check the apps/tools/setup pieces you want.
4. Look at the install total and current versions.
5. Use **Dry Run** if you want the exact plan.
6. Hit **Run Setup**.
7. Read the log if upstream did something weird or one manual tap is still needed.

## A few intentional limits

HandheldHero intentionally does **not** try to be clever about everything.

- No ROM/game/key/BIOS/firmware downloads.
- No mystery sigpatch mirrors.
- No replacing Obtainium when Obtainium already handles Android updates well.
- No deleting an SD card just because a ZIP has a root folder in it.
- No pretending `latest` is a meaningful version if upstream does not provide one.
- No hiding write operations behind a pretty button without a Dry Run path.

The project should stay understandable enough that if something breaks, I can figure out *why* without needing a conspiracy board.

## Project status

Very much a work in progress, but it is past the random-script-on-my-desktop stage now.

Things I want to keep improving:

- more useful device-specific detection
- better installed-version detection
- better non-GitHub update checks
- cleaner Switch component/version detection
- HandheldHero self-update through GitHub releases
- eventually a nicer release/install flow for people who do not care what Python is

If a feature makes setup easier **and** keeps the tool understandable, I am probably interested in it.

If it adds fifteen layers of magic to save one click, probably not.

## Code style

The source is deliberately commented like a person explaining the weird parts to another person.

Comments should explain **why** something exists, especially around archive handling, version weirdness, backups, and upstream projects. They should not explain that `count += 1` increments a count. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full version of that rant.

## License

I have not picked a license yet. Until I do, assume normal copyright rules apply.
