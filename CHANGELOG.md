# Changelog

## v0.6

This is the first version I am treating like an actual project instead of a desktop experiment.

### Android

- ADB device detection and basic Retroid / AYN Odin / Anbernic profiles.
- Android app/emulator/tool checklist with live upstream version labels.
- Installed-package detection with installed version labels where Android exposes them.
- Live **Selected / Already installed / Will install** totals.
- Direct first-install support plus Obtainium JSON generation for ongoing updates.
- Steam and Steam Link stay on the Play Store path instead of using random APK mirrors.
- Daijisho frontend support.

### Switch

- Base SD build/update using current Hekate + Atmosphere releases.
- Hekate, Nyx, Atmosphere, hbloader, hbmenu, and fusee version tracking.
- Optional Sphaira, HB App Store, MissionControl, sys-clk, Ultrahand, NXThemesInstaller, JKSV, FTPD, and NX-Shell.
- Version manifest on the SD so update checks can compare what HandheldHero installed against upstream.
- Backup-before-overwrite behavior for base/root package merges.
- Local firmware staging.
- Local sigpatch staging without silently merging unknown packs.

### General

- Matching BIOS / firmware / sigpatch source pickers: None, Local ZIP, Local folder.
- Dry Run plan before setup.
- Post-run verification checks.
- Source version cache so startup does not hammer GitHub.
- Human-readable comments throughout the source.
- Renamed the project from RetroCommander to HandheldHero because that name is way better lol.
