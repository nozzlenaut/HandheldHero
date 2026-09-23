# HandheldHero
#
# One Windows utility for setting up the handhelds I actually use. The goal is simple:
# plug in an Android handheld or SD card, pick what you want, see exactly what is about
# to happen, and let the boring setup work happen in one place.
#
# This is intentionally a single-file app for now. It is easier to carry around, easier
# to turn into an EXE, and easier to understand when something inevitably gets weird.

import json, os, re, shutil, subprocess, sys, tempfile, threading, urllib.parse, urllib.request, zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "HandheldHero"
APP_VERSION = "0.6"
PACK_URL = "https://raw.githubusercontent.com/RJNY/Obtainium-Emulation-Pack/main/obtainium-emulation-pack-latest.json"

# New installs use the new name. If somebody already ran v0.6, keep using the old
# data folder instead of making their backups/cache look like they vanished overnight.
NEW_DATA_DIR = Path.home() / "Documents" / APP_NAME
LEGACY_DATA_DIR = Path.home() / "Documents" / "Handheld Setup"
DATA_DIR = LEGACY_DATA_DIR if LEGACY_DATA_DIR.exists() and not NEW_DATA_DIR.exists() else NEW_DATA_DIR
DOWNLOAD_DIR = DATA_DIR / "Downloads"
BACKUP_DIR = DATA_DIR / "Backups"

# Same deal on a Switch SD: write new metadata under the new name, but still read the
# old v0.6 folder so update checks keep working after the rename.
META_DIR_NAME = "_HandheldHero"
LEGACY_META_DIR_NAME = "_HandheldSetup"
for d in (DATA_DIR, DOWNLOAD_DIR, BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Android app catalog -------------------------------------------------------
# These names are what the UI shows. The values map back to Obtainium or one of the
# small custom resolvers below when upstream does not fit the normal path.
ANDROID_APPS = {
    "RetroArch (AArch64)": "RetroArch (AArch64)",
    "PPSSPP": "PPSSPP",
    "Dolphin": "Dolphin Emulator",
    "DuckStation": "DuckStation",
    "Azahar (3DS)": "Azahar",
    "melonDS": "MelonDS",
    "Flycast": "Flycast",
    "Moonlight": "Moonlight",
    "Syncthing-Fork": "Syncthing-Fork",
    "Winlator": "Winlator",
    "hakuX (Original Xbox)": "__HAKUX__",
    "X360 Mobile": "X360 Mobile",
    "Eden (Switch)": "Eden",
    "Citron Neo (Switch)": "Citron Neo",
    "Steam (Play Store)": "__STEAM__",
    "Steam Link (Play Store)": "__STEAMLINK__",
}

ANDROID_FRONTENDS = {
    "Daijisho": "__DAIJISHO__",
}

ANDROID_CHOICES = {**ANDROID_APPS, **ANDROID_FRONTENDS}

ANDROID_PACKAGES = {
    "RetroArch (AArch64)":"com.retroarch.aarch64",
    "PPSSPP":"org.ppsspp.ppsspp",
    "Dolphin":"org.dolphinemu.dolphinemu",
    "DuckStation":"com.github.stenzek.duckstation",
    "Azahar (3DS)":"org.azahar_emu.azahar",
    "melonDS":"me.magnum.melonds",
    "Flycast":"com.flycast.emulator",
    "Moonlight":"com.limelight",
    "Syncthing-Fork":"com.github.catfriend1.syncthingfork",
    "Winlator":"com.winlator",
    "X360 Mobile":"emu.x360mobile.com",
    "Eden (Switch)":"dev.eden.eden_emulator",
    "Citron Neo (Switch)":"org.citron.citron_emu",
    "Steam (Play Store)":"com.valvesoftware.android.steam.community",
    "Steam Link (Play Store)":"com.valvesoftware.steamlink",
    "Daijisho":"com.magneticchen.daijishou",
}

PLAY_STORE_APPS = {
    "Steam (Play Store)":"com.valvesoftware.android.steam.community",
    "Steam Link (Play Store)":"com.valvesoftware.steamlink",
}

# --- Switch app catalog --------------------------------------------------------
# Normal Switch apps land under /switch. Root packages are the ones that ship an
# Atmosphere/config/overlay tree and need to be merged onto the SD card instead.
SWITCH_APPS = {
    "JKSV save manager": ("J-D-K/JKSV", r"(?i)\.nro$"),
    "FTPD file transfer": ("mtheall/ftpd", r"(?i)\.nro$"),
    "NX-Shell file manager": ("joel16/NX-Shell", r"(?i)\.nro$"),
    "NXThemesInstaller": ("exelix11/SwitchThemeInjector", r"(?i)^NXThemesInstaller\.nro$"),
}

SWITCH_ROOT_PACKAGES = {
    "Sphaira homebrew menu": ("NaGaa95/sphaira", r"(?i)^sphaira\.zip$"),
    "HB App Store": ("fortheusers/hb-appstore", r"(?i)^switch-extracttosd\.zip$"),
    "MissionControl": ("ndeadly/MissionControl", r"(?i)^MissionControl-.*\.zip$"),
    "sys-clk": ("retronx-team/sys-clk", r"(?i)^sys-clk-.*\.zip$"),
    "Ultrahand Overlay": ("ppkantorski/Ultrahand-Overlay", r"(?i)^sdout\.zip$"),
}

# Used only for version badges/update checks. Actual Android updating is left to
# Obtainium whenever Obtainium already does the job well.
ANDROID_GITHUB_REPOS = {
    "Azahar (3DS)":"azahar-emu/azahar",
    "melonDS":"rafaelvcaetano/melonDS-android",
    "Flycast":"flyinghead/flycast",
    "Moonlight":"moonlight-stream/moonlight-android",
    "Syncthing-Fork":"researchxxl/syncthing-android",
    "Winlator":"brunodev85/winlator",
    "hakuX (Original Xbox)":"rfandango/hakuX",
    "X360 Mobile":"Ashnar2602/X360-Mobile---OFFICIAL",
    "Citron Neo (Switch)":"citron-neo/emulator",
    "Daijisho":"TapiocaFox/Daijishou",
}

# Profiles are deliberately broad. I would rather show an option and grey it out
# correctly than pretend every Anbernic/Retroid/Odin needs its own giant code path.
PROFILES = [
    "Auto detect",
    "Generic Android",
    "Retroid / Android",
    "AYN Odin / Android",
    "Anbernic Android",
    "TrimUI Brick (CrossMix/Stock)",
    "TrimUI Brick (MinUI)",
    "Generic Linux handheld SD",
    "Modded Switch SD",
]

ANDROID_PROFILES = {"Generic Android","Retroid / Android","AYN Odin / Android","Anbernic Android"}
SWITCH_PROFILE = "Modded Switch SD"

# Folder names are kept boring on purpose so frontends/emulators can find them.
ROM_DIRS_ANDROID = ["NES","SNES","N64","GB","GBC","GBA","GENESIS","PSX","PSP","NDS","3DS","GC","WII","DREAMCAST"]
ROM_DIRS_TRIMUI = ["FC","SFC","N64","GB","GBC","GBA","MD","PS","PSP","NDS","DC"]

# Small HTTP helper so every download uses the same timeout/User-Agent instead of repeating boilerplate everywhere.
def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent":f"{APP_NAME}/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# Run a command quietly on Windows and give the caller stdout/stderr instead of throwing away the useful bits.
def run(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

# Find ADB from PATH first, then fall back to the normal WinGet Platform Tools location.
def adb_path():
    found = shutil.which("adb")
    if found:
        return found
    candidates = list((Path.home()/ "AppData/Local/Microsoft/WinGet/Packages").glob("Google.PlatformTools_*/*/adb.exe"))
    return str(candidates[0]) if candidates else "adb"

# Build an ADB command with an optional serial. Multiple handhelds plugged in at once should not become a guessing game.
def adb(args, serial=None, timeout=60):
    cmd = [adb_path()]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    return run(cmd, timeout=timeout)

# Grab GitHub latest-release JSON in one place. A bunch of version/install paths need the same data.
def github_latest_release(repo):
    return json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest").decode("utf-8"))

# Pick one release asset by regex. Some projects dump a pile of files into each release, so filename matching is safer than assuming asset #1.
def github_latest_asset(repo, pattern, prefer_arm64=False):
    data = github_latest_release(repo)
    assets = [a for a in data.get("assets", []) if re.search(pattern, a.get("name",""))]
    if prefer_arm64:
        arm = [a for a in assets if re.search(r"(?i)(arm64|aarch64|v8a)", a.get("name",""))]
        if arm:
            assets = arm
    if not assets:
        raise RuntimeError(f"No matching release asset for {repo}")
    return assets[0]["browser_download_url"], assets[0]["name"]
# GitHub tags are inconsistent about a leading v. Strip it so the UI does not end up saying vv1.2.3.
def clean_version(value):
    value = str(value or "").strip()
    if not value:
        return "unknown"
    return value[1:] if value.lower().startswith("v") else value

# Read the Switch base versions we care about, including versions buried inside Hekate/Atmosphere asset filenames.
def latest_switch_versions():
    hek = github_latest_release("CTCaer/hekate")
    atm = github_latest_release("Atmosphere-NX/Atmosphere")
    versions = {
        "hekate": clean_version(hek.get("tag_name")),
        "atmosphere": clean_version(atm.get("tag_name")),
    }
    try:
        hek_zip = next(a.get("name","") for a in hek.get("assets",[]) if re.search(r"(?i)_Nyx_.*\.zip$",a.get("name","")))
        m = re.search(r"_Nyx_([0-9.]+)\.zip$",hek_zip,re.I)
        if m:
            versions["nyx"] = m.group(1)
    except Exception:
        pass
    try:
        atm_zip = next(a.get("name","") for a in atm.get("assets",[]) if a.get("name","").lower().endswith(".zip"))
        mh = re.search(r"\+hbl-([^+]+)\+",atm_zip,re.I)
        mm = re.search(r"\+hbmenu-([0-9.]+)\.zip$",atm_zip,re.I)
        if mh:
            versions["hbl"] = mh.group(1)
        if mm:
            versions["hbmenu"] = mm.group(1)
    except Exception:
        pass
    return versions

# Build the version badges shown in the UI. Cache them for a few hours so opening the app does not hammer GitHub for no reason.
def current_source_versions(force=False):
    cache_path = DATA_DIR / "source_versions.json"
    if not force and cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(cached.get("fetched_at",""))
            if (datetime.now() - fetched).total_seconds() < 21600:
                return cached.get("versions",{})
        except Exception:
            pass
    versions = {}
    for name,repo in ANDROID_GITHUB_REPOS.items():
        try:
            data = github_latest_release(repo)
            versions[name] = clean_version(data.get("tag_name"))
        except Exception:
            versions[name] = "unknown"
    try:
        versions["RetroArch (AArch64)"] = re.search(r"RetroArch-([0-9.]+)-", resolve_retroarch()[1]).group(1)
    except Exception:
        versions["RetroArch (AArch64)"] = "unknown"
    try:
        url,_ = resolve_html_apk("PPSSPP")
        m = re.search(r"/files/([0-9_]+)/", url)
        versions["PPSSPP"] = m.group(1).replace("_",".") if m else "unknown"
    except Exception:
        versions["PPSSPP"] = "unknown"
    try:
        _,name = resolve_html_apk("Dolphin")
        m = re.search(r"dolphin-([^-]+)\.apk", name, re.I)
        versions["Dolphin"] = m.group(1) if m else "unknown"
    except Exception:
        versions["Dolphin"] = "unknown"
    try:
        data = github_latest_release("stenzek/duckstation")
        published = str(data.get("published_at", ""))[:10]
        versions["DuckStation"] = f"rolling {published}" if published else "rolling"
    except Exception:
        versions["DuckStation"] = "rolling"
    try:
        data = json.loads(http_get("https://stable.eden-emu.dev/latest/release.json").decode("utf-8"))
        versions["Eden (Switch)"] = clean_version(data.get("tag_name"))
    except Exception:
        versions["Eden (Switch)"] = "unknown"
    for name,(repo,_) in {**SWITCH_APPS, **SWITCH_ROOT_PACKAGES}.items():
        try:
            versions[name] = clean_version(github_latest_release(repo).get("tag_name"))
        except Exception:
            versions[name] = "unknown"
    try:
        sv = latest_switch_versions()
        parts = [f"Hekate {sv['hekate']}"]
        if sv.get("nyx"):
            parts.append(f"Nyx {sv['nyx']}")
        parts.append(f"Atmosphere {sv['atmosphere']}")
        if sv.get("hbmenu"):
            parts.append(f"hbmenu {sv['hbmenu']}")
        versions["__SWITCH_BASE__"] = " / ".join(parts)
    except Exception:
        versions["__SWITCH_BASE__"] = "unknown"
    try:
        cache_path.write_text(json.dumps({"fetched_at":datetime.now().isoformat(timespec="seconds"),"versions":versions},indent=2),encoding="utf-8")
    except Exception:
        pass
    return versions

# Stream downloads in chunks. Keeping this here also gives us one place to add checksums/progress later.
def download(url, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent":f"{APP_NAME}/{APP_VERSION}"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            block = r.read(1024 * 1024)
            if not block:
                break
            f.write(block)
    return dest

# Ask ADB what Android devices are actually connected and turn them into the same target shape used by SD cards.
def get_android_devices():
    try:
        out = adb(["devices","-l"], timeout=10).stdout.splitlines()
    except Exception:
        return []
    devices = []
    for line in out[1:]:
        if "\tdevice" not in line:
            continue
        serial = line.split()[0]
        fields = dict(re.findall(r"(\w+):([^\s]+)", line))
        model = fields.get("model","Android").replace("_"," ")
        devices.append({"kind":"android","serial":serial,"label":f"Android: {model} [{serial}]","model":model})
    return devices

# Find Windows removable drives with PowerShell. Drive letters are less annoying than trying to guess where an SD card mounted.
def get_removable_drives():
    ps = r"""Get-CimInstance Win32_LogicalDisk | Where-Object {$_.DriveType -eq 2} | Select-Object DeviceID,VolumeName,FileSystem | ConvertTo-Json -Compress"""
    try:
        r = run(["powershell","-NoProfile","-Command",ps], timeout=10)
        if not r.stdout.strip():
            return []
        data = json.loads(r.stdout)
        if isinstance(data, dict):
            data = [data]
    except Exception:
        return []
    drives = []
    for d in data:
        root = str(d.get("DeviceID","")) + "\\"
        if not root or not Path(root).exists():
            continue
        label = d.get("VolumeName") or "Removable"
        drives.append({"kind":"drive","root":root,"label":f"SD/USB: {label} ({root})"})
    return drives

# Make a best-effort guess at what kind of SD card this is from folders that should already exist.
def classify_drive(root):
    p = Path(root)
    if (p/"atmosphere").exists() or ((p/"switch").exists() and (p/"Nintendo").exists()):
        return "Modded Switch SD"
    if (p/"trimui").exists() and (p/"Roms").exists():
        if (p/"MinUI.zip").exists() or (p/".userdata").exists():
            return "TrimUI Brick (MinUI)"
        return "TrimUI Brick (CrossMix/Stock)"
    if (p/"Bios").exists() and (p/"Roms").exists():
        return "Generic Linux handheld SD"
    return "Generic Linux handheld SD"

# Use manufacturer/model properties to choose a useful Android profile without hard-coding every device ever made.
def classify_android(serial):
    # Tiny local helper because reading Android properties five times should not require five nearly identical ADB calls.
    def prop(name):
        return adb(["shell","getprop",name], serial=serial, timeout=8).stdout.strip()
    maker = prop("ro.product.manufacturer").lower()
    model = prop("ro.product.model").lower()
    combo = maker + " " + model
    if "retroid" in combo:
        return "Retroid / Android"
    if "ayn" in combo or "odin" in combo:
        return "AYN Odin / Android"
    if "anbernic" in combo:
        return "Anbernic Android"
    return "Generic Android"
# Pull the community Obtainium emulation pack that covers most Android apps better than maintaining another giant list here.
def fetch_obtainium_pack():
    return json.loads(http_get(PACK_URL).decode("utf-8"))

# hakuX is not represented exactly how we need in the upstream pack, so describe it to Obtainium ourselves.
def hakux_entry():
    return {
        "id":"org.hakux",
        "url":"https://github.com/rfandango/hakuX",
        "author":"rfandango",
        "name":"hakuX",
        "preferredApkIndex":0,
        "additionalSettings":json.dumps({
            "includePrereleases":False,"fallbackToOlderReleases":True,
            "trackOnly":False,"apkFilterRegEx":"(?i)\\.apk$",
            "autoApkFilterByArch":True,"about":"Original Xbox/xemu fork for Android"
        }, separators=(",",":")),
        "categories":["Emulator"],
        "allowIdChange":True,
        "overrideSource":"GitHub"
    }

# Same idea as hakuX: give Obtainium a clean Daijisho entry without making the user build JSON by hand.
def daijisho_entry():
    return {
        "id":"com.magneticchen.daijishou",
        "url":"https://github.com/TapiocaFox/Daijishou",
        "author":"TapiocaFox",
        "name":"Daijisho",
        "preferredApkIndex":0,
        "additionalSettings":json.dumps({
            "includePrereleases":False,"fallbackToOlderReleases":True,
            "trackOnly":False,"apkFilterRegEx":"(?i)\\.apk$",
            "autoApkFilterByArch":False,"about":"Android emulation frontend"
        }, separators=(",",":")),
        "categories":["Frontend"],
        "allowIdChange":False,
        "overrideSource":"GitHub"
    }

# Take the huge Obtainium pack and write a tiny device-specific JSON containing only the apps the user checked.
def build_filtered_pack(selected):
    pack = fetch_obtainium_pack()
    wanted = {ANDROID_CHOICES[x] for x in selected if not ANDROID_CHOICES[x].startswith("__")}
    apps = [a for a in pack.get("apps",[]) if a.get("name") in wanted]
    if any(ANDROID_CHOICES[x] == "__HAKUX__" for x in selected):
        apps.append(hakux_entry())
    if any(ANDROID_CHOICES[x] == "__DAIJISHO__" for x in selected):
        apps.append(daijisho_entry())
    out = {"apps":apps, "settings":pack.get("settings",{})}
    dest = DATA_DIR / "HandheldHero-Obtainium.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    return dest, apps

# RetroArch upstream is awkward to scrape reliably, so use the known stable direct APK and let Obtainium handle future updates.
def resolve_retroarch():
    # h5ai's live index hides directory names behind JavaScript, so use the
    # current known stable for first install. Obtainium tracks future updates.
    v = "1.22.2"
    return f"https://buildbot.libretro.com/stable/{v}/android/RetroArch_aarch64.apk", f"RetroArch-{v}-aarch64.apk"

# Eden publishes a machine-readable release file. Prefer its standard Android APK instead of guessing from filenames.
def resolve_eden():
    data = json.loads(http_get("https://stable.eden-emu.dev/latest/release.json").decode("utf-8"))
    assets = data.get("assets", [])
    preferred = [a for a in assets if a.get("name","").endswith("-standard.apk")]
    if not preferred:
        preferred = [a for a in assets if a.get("name","").endswith(".apk") and "chromeos" not in a.get("name","").lower()]
    if not preferred:
        raise RuntimeError("Could not find Eden Android APK")
    a = preferred[0]
    return a["browser_download_url"], a["name"]

# A few projects do not fit the normal GitHub-release path. Resolve their official/current APK from the source they actually publish.
def resolve_html_apk(name):
    if name == "RetroArch (AArch64)":
        return resolve_retroarch()
    if name == "PPSSPP":
        html = http_get("https://www.ppsspp.org/download/").decode("utf-8","ignore")
        links = re.findall(r'href=["\']([^"\']*ppsspp\.apk)["\']', html, re.I)
    elif name == "Dolphin":
        req = urllib.request.Request("https://dolphin-emu.org/download/?ref=btn", headers={"User-Agent":"Obtainium/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        url = data.get("beta") or data.get("dev")
        if not url:
            raise RuntimeError("Could not find Dolphin APK")
        return url, Path(urllib.parse.urlparse(url).path).name
    elif name == "DuckStation":
        req = urllib.request.Request("https://duckstation-mirror.rmacias.workers.dev", headers={"User-Agent":"Obtainium/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8","ignore")
        links = re.findall(r'href=["\']([^"\']+\.apk)["\']', html, re.I)
    else:
        raise RuntimeError("No HTML resolver")
    if not links:
        raise RuntimeError(f"Could not find APK for {name}")
    url = urllib.parse.urljoin("https://www.ppsspp.org/download/" if name=="PPSSPP" else "https://duckstation-mirror.rmacias.workers.dev", links[0])
    return url, Path(urllib.parse.urlparse(url).path).name or (name+".apk")
# Turn an Obtainium entry into a direct APK for first install. Obtainium still owns updates after that.
def resolve_from_pack(display_name, pack_app):
    if display_name in ("RetroArch (AArch64)","PPSSPP","Dolphin","DuckStation"):
        return resolve_html_apk(display_name)
    if display_name == "hakuX (Original Xbox)":
        return github_latest_asset("rfandango/hakuX", r"(?i)\.apk$")
    if display_name == "Eden (Switch)":
        return resolve_eden()
    if display_name == "Daijisho":
        return github_latest_asset("TapiocaFox/Daijishou", r"(?i)\.apk$")
    url = pack_app.get("url","")
    m = re.match(r"https://github\.com/([^/]+/[^/]+)", url)
    if not m:
        raise RuntimeError("This app is tracked through a non-GitHub source; Obtainium will handle it")
    repo = m.group(1).rstrip("/")
    settings = pack_app.get("additionalSettings",{})
    if isinstance(settings, str):
        try: settings = json.loads(settings)
        except Exception: settings = {}
    regex = settings.get("apkFilterRegEx") or r"(?i)\.apk$"
    data = json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest").decode("utf-8"))
    assets = [a for a in data.get("assets",[]) if a.get("name","").lower().endswith(".apk")]
    try:
        filtered = [a for a in assets if re.search(regex, a.get("name",""), re.I)]
        if filtered: assets = filtered
    except re.error:
        pass
    arm = [a for a in assets if re.search(r"(?i)(arm64|aarch64|v8a)", a.get("name",""))]
    if settings.get("autoApkFilterByArch") and arm:
        assets = arm
    if not assets:
        raise RuntimeError(f"No APK asset found for {display_name}")
    idx = int(pack_app.get("preferredApkIndex") or 0)
    idx = min(max(idx,0), len(assets)-1)
    a = assets[idx]
    return a["browser_download_url"], a["name"]

# Copy a folder tree while saving anything we are about to overwrite. Boring backups beat exciting recovery stories.
def copy_tree_with_backup(src, dst, backup_root):
    src, dst = Path(src), Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            b = Path(backup_root) / rel
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, b)
        shutil.copy2(item, target)
        count += 1
    return count

# Cheap Android path existence check used before trying to back up folders that may not exist.
def android_exists(serial, path):
    r = adb(["shell","sh","-c",f'test -e "{path}" && echo yes'], serial=serial, timeout=10)
    return "yes" in r.stdout

# Single-file version of the backup-before-overwrite rule.
def copy_with_backup(src, dst, backup_root):
    src, dst, backup_root = Path(src), Path(dst), Path(backup_root)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        rel = Path(dst.name)
        b = backup_root / rel
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, b)
    shutil.copy2(src, dst)

# Safely merge a ZIP onto an SD root. Reject path traversal and back up replaced files instead of blindly exploding archives.
def extract_zip_merge_with_backup(zip_path, root, backup_root, skip_top_level=None):
    root, backup_root = Path(root), Path(backup_root)
    skip_top_level = set(skip_top_level or [])
    count = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = Path(info.filename)
            if rel.is_absolute() or ".." in rel.parts:
                continue
            if len(rel.parts) == 1 and rel.name in skip_top_level:
                continue
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                b = backup_root / rel
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, b)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count

# --- Main application ----------------------------------------------------------
# Tkinter is not glamorous, but it is already on Python, works fine on Windows, and
# keeps this from turning into a web stack just to draw some checkboxes.
class HandheldHeroApp:
    # Create all UI state first, wire checkbox changes into the live summary, then kick off version/device scans after Tk is alive.
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1000x960")
        self.root.minsize(900,800)
        self.targets = []
        self.target_var = tk.StringVar()
        self.profile_var = tk.StringVar(value="Auto detect")
        self.status_var = tk.StringVar(value="No device scanned yet")
        self.summary_var = tk.StringVar(value="Selected 0")
        self.update_status_var = tk.StringVar(value="Updates not checked")
        self.installed_packages = set()
        self.installed_versions = {}
        self.source_versions = {}
        self.bios_mode_var = tk.StringVar(value="None")
        self.bios_var = tk.StringVar()
        self.backup_var = tk.BooleanVar(value=True)
        self.romdirs_var = tk.BooleanVar(value=True)
        self.install_now_var = tk.BooleanVar(value=True)
        self.obtainium_var = tk.BooleanVar(value=True)
        self.verify_var = tk.BooleanVar(value=True)
        self.switch_base_var = tk.BooleanVar(value=False)
        self.sigpatch_mode_var = tk.StringVar(value="None")
        self.sigpatch_path_var = tk.StringVar()
        self.firmware_mode_var = tk.StringVar(value="None")
        self.firmware_path_var = tk.StringVar()
        self.app_vars = {name:tk.BooleanVar(value=False) for name in ANDROID_APPS}
        self.frontend_vars = {name:tk.BooleanVar(value=False) for name in ANDROID_FRONTENDS}
        self.switch_vars = {name:tk.BooleanVar(value=False) for name in SWITCH_APPS}
        self.switch_root_vars = {name:tk.BooleanVar(value=False) for name in SWITCH_ROOT_PACKAGES}
        self.android_widgets = []
        self.frontend_widgets = []
        self.switch_widgets = []
        self.android_widget_by_name = {}
        self.frontend_widget_by_name = {}
        self.switch_widget_by_name = {}
        self.build_ui()
        for var in list(self.app_vars.values()) + list(self.frontend_vars.values()) + list(self.switch_vars.values()) + list(self.switch_root_vars.values()) + [
            self.switch_base_var,self.sigpatch_mode_var,self.firmware_mode_var,self.bios_mode_var,
            self.install_now_var,self.obtainium_var,self.romdirs_var
        ]:
            var.trace_add("write", lambda *_: self.update_summary())
        self.root.after(100, lambda: threading.Thread(target=self.load_source_versions,daemon=True).start())
        self.root.after(150, self.refresh_devices)

    # Build the entire window in one place. The sections intentionally follow the order somebody actually sets up a handheld.
    def build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=APP_NAME, font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(outer, text="Detect, install, copy BIOS, build ROM folders, and keep Android apps updated.").pack(anchor="w", pady=(0,10))

        conn = ttk.LabelFrame(outer, text="1. Device", padding=10)
        conn.pack(fill="x")
        ttk.Label(conn, textvariable=self.status_var).grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,6))
        ttk.Label(conn,text="Target").grid(row=1,column=0,sticky="w")
        self.target_combo = ttk.Combobox(conn,textvariable=self.target_var,state="readonly",width=56)
        self.target_combo.grid(row=1,column=1,sticky="ew",padx=6)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_change)
        ttk.Button(conn,text="Refresh",command=self.refresh_devices).grid(row=1,column=2,padx=4)
        ttk.Button(conn,text="Browse SD root",command=self.browse_target).grid(row=1,column=3,padx=4)
        ttk.Label(conn,text="Profile").grid(row=2,column=0,sticky="w",pady=(8,0))
        self.profile_combo = ttk.Combobox(conn,textvariable=self.profile_var,values=PROFILES,state="readonly",width=34)
        self.profile_combo.grid(row=2,column=1,sticky="w",padx=6,pady=(8,0))
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)
        conn.columnconfigure(1,weight=1)

        summary = ttk.Frame(outer)
        summary.pack(fill="x",pady=(8,0))
        ttk.Label(summary,textvariable=self.summary_var,font=("Segoe UI",10,"bold")).pack(side="left")
        ttk.Label(summary,textvariable=self.update_status_var).pack(side="right")

        apps = ttk.LabelFrame(outer,text="2. Android apps / emulators / tools",padding=10)
        apps.pack(fill="x",pady=(10,6))
        for i,(name,var) in enumerate(self.app_vars.items()):
            cb = ttk.Checkbutton(apps,text=name,variable=var)
            cb.grid(row=i//4,column=i%4,sticky="w",padx=(0,18),pady=2)
            self.android_widgets.append(cb)
            self.android_widget_by_name[name] = cb

        front = ttk.LabelFrame(outer,text="Android frontends",padding=10)
        front.pack(fill="x",pady=(0,6))
        for i,(name,var) in enumerate(self.frontend_vars.items()):
            cb = ttk.Checkbutton(front,text=name,variable=var)
            cb.grid(row=0,column=i,sticky="w",padx=(0,24))
            self.frontend_widgets.append(cb)
            self.frontend_widget_by_name[name] = cb

        sw = ttk.LabelFrame(outer,text="Switch SD setup / homebrew",padding=10)
        sw.pack(fill="x",pady=(0,10))
        self.switch_base_cb = ttk.Checkbutton(sw,text="Base SD build/update (Hekate + Atmosphere + hbmenu/fusee)",variable=self.switch_base_var)
        self.switch_base_cb.grid(row=0,column=0,columnspan=4,sticky="w",pady=(0,5))
        self.switch_widgets.append(self.switch_base_cb)
        for i,(name,var) in enumerate(self.switch_root_vars.items()):
            cb = ttk.Checkbutton(sw,text=name,variable=var)
            cb.grid(row=1+i//3,column=i%3,sticky="w",padx=(0,18),pady=2)
            self.switch_widgets.append(cb)
            self.switch_widget_by_name[name] = cb
        normal_row = 1 + ((len(self.switch_root_vars)+2)//3)
        for i,(name,var) in enumerate(self.switch_vars.items()):
            cb = ttk.Checkbutton(sw,text=name,variable=var)
            cb.grid(row=normal_row+i//3,column=i%3,sticky="w",padx=(0,18),pady=2)
            self.switch_widgets.append(cb)
            self.switch_widget_by_name[name] = cb
        note_row = normal_row + ((len(self.switch_vars)+2)//3)
        ttk.Label(sw,text="Uses current official upstream releases and merges them onto the SD; existing overwritten files are backed up.").grid(row=note_row,column=0,columnspan=4,sticky="w",pady=(5,6))

        ttk.Label(sw,text="Sigpatches").grid(row=note_row+1,column=0,sticky="w")
        self.sigpatch_combo = ttk.Combobox(sw,textvariable=self.sigpatch_mode_var,values=["None","Local ZIP","Local folder"],state="readonly",width=18)
        self.sigpatch_combo.grid(row=note_row+1,column=1,sticky="w",padx=(6,8))
        self.sigpatch_entry = ttk.Entry(sw,textvariable=self.sigpatch_path_var,width=42)
        self.sigpatch_entry.grid(row=note_row+1,column=2,sticky="ew")
        self.sigpatch_browse_btn = ttk.Button(sw,text="Choose",command=lambda:self.choose_local_source("Sigpatches",self.sigpatch_mode_var,self.sigpatch_path_var))
        self.sigpatch_browse_btn.grid(row=note_row+1,column=3,padx=(8,0))
        self.switch_widgets += [self.sigpatch_combo,self.sigpatch_entry,self.sigpatch_browse_btn]

        ttk.Label(sw,text="Firmware").grid(row=note_row+2,column=0,sticky="w",pady=(5,0))
        self.firmware_combo = ttk.Combobox(sw,textvariable=self.firmware_mode_var,values=["None","Local ZIP","Local folder"],state="readonly",width=18)
        self.firmware_combo.grid(row=note_row+2,column=1,sticky="w",padx=(6,8),pady=(5,0))
        self.firmware_entry = ttk.Entry(sw,textvariable=self.firmware_path_var,width=42)
        self.firmware_entry.grid(row=note_row+2,column=2,sticky="ew",pady=(5,0))
        self.firmware_browse_btn = ttk.Button(sw,text="Choose",command=lambda:self.choose_local_source("Firmware",self.firmware_mode_var,self.firmware_path_var))
        self.firmware_browse_btn.grid(row=note_row+2,column=3,padx=(8,0),pady=(5,0))
        self.switch_widgets += [self.firmware_combo,self.firmware_entry,self.firmware_browse_btn]
        sw.columnconfigure(2,weight=1)

        opts = ttk.LabelFrame(outer,text="3. Setup options",padding=10)
        opts.pack(fill="x")
        ttk.Checkbutton(opts,text="Back up existing saves/configs first",variable=self.backup_var).grid(row=0,column=0,sticky="w")
        ttk.Checkbutton(opts,text="Create standard ROM folders",variable=self.romdirs_var).grid(row=0,column=1,sticky="w",padx=18)
        self.install_now_cb = ttk.Checkbutton(opts,text="Install selected Android apps now",variable=self.install_now_var)
        self.install_now_cb.grid(row=1,column=0,sticky="w",pady=4)
        self.obtainium_cb = ttk.Checkbutton(opts,text="Install Obtainium + build update JSON",variable=self.obtainium_var)
        self.obtainium_cb.grid(row=1,column=1,sticky="w",padx=18)
        ttk.Checkbutton(opts,text="Verify after setup",variable=self.verify_var).grid(row=2,column=0,sticky="w",pady=4)
        ttk.Label(opts,text="BIOS").grid(row=3,column=0,sticky="w",pady=(3,0))
        self.bios_combo = ttk.Combobox(opts,textvariable=self.bios_mode_var,values=["None","Local ZIP","Local folder"],state="readonly",width=18)
        self.bios_combo.grid(row=3,column=1,sticky="w",padx=(6,8),pady=(3,0))
        self.bios_entry = ttk.Entry(opts,textvariable=self.bios_var,width=42)
        self.bios_entry.grid(row=3,column=2,sticky="ew",pady=(3,0))
        self.bios_browse_btn = ttk.Button(opts,text="Choose",command=lambda:self.choose_local_source("BIOS",self.bios_mode_var,self.bios_var))
        self.bios_browse_btn.grid(row=3,column=3,padx=(8,0),pady=(3,0))
        opts.columnconfigure(2,weight=1)
        self.update_compatibility()

        controls = ttk.Frame(outer)
        controls.pack(fill="x",pady=10)
        self.run_btn = ttk.Button(controls,text="RUN SETUP",command=self.start_setup)
        self.run_btn.pack(side="left")
        ttk.Button(controls,text="Dry Run",command=self.dry_run).pack(side="left",padx=(8,0))
        ttk.Button(controls,text="Check updates",command=self.check_updates).pack(side="left",padx=(8,0))
        ttk.Button(controls,text="Open backups",command=lambda:os.startfile(BACKUP_DIR)).pack(side="left",padx=8)
        ttk.Button(controls,text="Open data folder",command=lambda:os.startfile(DATA_DIR)).pack(side="left")

        self.logbox = tk.Text(outer,height=14,wrap="word",state="disabled")
        self.logbox.pack(fill="both",expand=True)
    # Write timestamped messages into the GUI from either the main thread or worker threads.
    def log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        # Tk widgets must be touched on Tk's thread, so the actual text insertion lives in this tiny scheduled callback.
        def write():
            self.logbox.configure(state="normal")
            self.logbox.insert("end", f"[{stamp}] {msg}\n")
            self.logbox.see("end")
            self.logbox.configure(state="disabled")
        self.root.after(0, write)

    # Format whatever upstream calls a version without pretending dates/rolling builds are semantic versions.
    def version_badge(self, version):
        version = str(version or "").strip()
        if not version or version == "unknown":
            return "version ?"
        if version.startswith("rolling "):
            return version
        if re.match(r"^\d{4}-\d{2}-\d{2}$", version) or "/" in version or version.lower().startswith("nxt-"):
            return version
        return f"v{version}"

    # Build one readable checkbox label from source version + installed state.
    def choice_label(self, name):
        version = self.source_versions.get(name)
        if name in PLAY_STORE_APPS:
            installed = self.installed_versions.get(name)
            suffix = f"v{installed}" if installed else "Play Store"
        elif version and version != "unknown":
            suffix = self.version_badge(version)
        else:
            suffix = "version ?"
        pkg = ANDROID_PACKAGES.get(name)
        installed_mark = " ✓ installed" if pkg and pkg in self.installed_packages else ""
        return f"{name} ({suffix}){installed_mark}"

    # Refresh every app label after source versions or installed-package data changes.
    def refresh_version_labels(self):
        for name,widget in self.android_widget_by_name.items():
            widget.configure(text=self.choice_label(name))
        for name,widget in self.frontend_widget_by_name.items():
            widget.configure(text=self.choice_label(name))
        for name,widget in self.switch_widget_by_name.items():
            version = self.source_versions.get(name,"unknown")
            widget.configure(text=f"{name} ({self.version_badge(version)})")
        base = self.source_versions.get("__SWITCH_BASE__")
        self.switch_base_cb.configure(text=f"Base SD build/update ({base})" if base else "Base SD build/update (Hekate + Atmosphere + hbmenu/fusee)")

    # Load cached/current upstream versions in the background so startup stays responsive.
    def load_source_versions(self):
        self.root.after(0,lambda:self.update_status_var.set("Loading current versions..."))
        versions = current_source_versions()
        self.source_versions = versions
        self.root.after(0,self.refresh_version_labels)
        self.root.after(0,lambda:self.update_status_var.set("Current versions loaded"))

    # BIOS, firmware, and sigpatches deliberately use the same picker behavior. One pattern is easier to understand than three special cases.
    def choose_local_source(self, label, mode_var, path_var):
        mode = mode_var.get()
        if mode == "Local ZIP":
            p = filedialog.askopenfilename(title=f"Choose {label} ZIP",filetypes=[("ZIP archives","*.zip"),("All files","*.*")])
        elif mode == "Local folder":
            p = filedialog.askdirectory(title=f"Choose {label} folder")
        else:
            messagebox.showinfo(label,f"Choose Local ZIP or Local folder for {label} first.")
            return
        if p:
            path_var.set(p)

    # Allow a manually selected folder/SD root when Windows removable-drive detection is not enough.
    def browse_target(self):
        p = filedialog.askdirectory(title="Choose handheld or Switch SD-card root")
        if not p:
            return
        target = {"kind":"drive","root":p,"label":f"Folder/SD: {Path(p).name or p} ({p})"}
        self.targets.append(target)
        self.target_combo["values"] = [x["label"] for x in self.targets]
        self.target_var.set(target["label"])
        self.on_target_change()

    # Scan Android + removable drives off the UI thread, then update the target dropdown when the results are ready.
    def refresh_devices(self):
        self.status_var.set("Scanning...")
        # Background worker. Network/ADB/disk scans should not freeze the window while Windows thinks about life.
        def work():
            targets = get_android_devices() + get_removable_drives()
            self.targets = targets
            labels = [x["label"] for x in targets]
            # Apply scan results back on the Tk thread once the background work is finished.
            def update():
                self.target_combo["values"] = labels
                if labels:
                    self.target_var.set(labels[0])
                    self.status_var.set(f"Found {len(labels)} target(s)")
                    self.on_target_change()
                else:
                    self.target_var.set("")
                    self.status_var.set("No Android ADB device or removable SD card found")
            self.root.after(0, update)
        threading.Thread(target=work,daemon=True).start()

    # Translate the target dropdown text back into the target dictionary the rest of the app uses.
    def selected_target(self):
        label = self.target_var.get()
        for t in self.targets:
            if t["label"] == label:
                return t
        return None

    # A profile change mostly means recalculating which controls make sense and what the summary should say.
    def on_profile_change(self, _event=None):
        self.update_compatibility()
        self.update_summary()

    # Grey out controls that do not make sense for the selected platform. Disabled is better than letting a nonsense combination fail later.
    def update_compatibility(self):
        profile = self.profile_var.get()
        android_ok = profile in ANDROID_PROFILES or profile == "Auto detect"
        switch_ok = profile == SWITCH_PROFILE or profile == "Auto detect"
        for w in self.android_widgets + self.frontend_widgets:
            w.configure(state="normal" if android_ok else "disabled")
        for w in self.switch_widgets:
            w.configure(state="normal" if switch_ok else "disabled")
        self.sigpatch_combo.configure(state="readonly" if switch_ok else "disabled")
        self.firmware_combo.configure(state="readonly" if switch_ok else "disabled")
        self.install_now_cb.configure(state="normal" if android_ok else "disabled")
        self.obtainium_cb.configure(state="normal" if android_ok else "disabled")

    # Auto-detect the profile for the newly selected target and scan installed Android packages when applicable.
    def on_target_change(self, _event=None):
        t = self.selected_target()
        if not t:
            self.update_compatibility()
            return
        if self.profile_var.get() != "Auto detect" and _event is None:
            pass
        try:
            profile = classify_android(t["serial"]) if t["kind"]=="android" else classify_drive(t["root"])
            self.profile_var.set(profile)
            self.status_var.set(f"{t['label']} -> {profile}")
            self.update_compatibility()
            self.update_summary()
            if t["kind"] == "android":
                threading.Thread(target=self.scan_installed_android,args=(t["serial"],),daemon=True).start()
        except Exception as e:
            self.status_var.set(f"{t['label']} (profile detection failed: {e})")

    # Validate local file/folder choices before starting any writes. Fail early while nothing has been touched yet.
    def start_setup(self):
        t = self.selected_target()
        if not t:
            messagebox.showwarning("No device","Connect an Android device with USB debugging, or insert/mount an SD card.")
            return
        for label,mode_var,path_var in [
            ("BIOS",self.bios_mode_var,self.bios_var),
        ]:
            mode = mode_var.get()
            raw = path_var.get().strip()
            src = Path(raw) if raw else None
            if mode == "Local ZIP" and (not src or not src.is_file() or src.suffix.lower() != ".zip"):
                messagebox.showwarning(label,f"Choose a valid {label} ZIP.")
                return
            if mode == "Local folder" and (not src or not src.is_dir()):
                messagebox.showwarning(label,f"Choose a valid {label} folder.")
                return
        profile = self.profile_var.get()
        if profile == SWITCH_PROFILE:
            for label,mode_var,path_var in [
                ("Sigpatches",self.sigpatch_mode_var,self.sigpatch_path_var),
                ("Firmware",self.firmware_mode_var,self.firmware_path_var),
            ]:
                mode = mode_var.get()
                raw = path_var.get().strip()
                src = Path(raw) if raw else None
                if mode == "Local ZIP" and (not src or not src.is_file() or src.suffix.lower() != ".zip"):
                    messagebox.showwarning(label,f"Choose a valid {label} ZIP.")
                    return
                if mode == "Local folder" and (not src or not src.is_dir()):
                    messagebox.showwarning(label,f"Choose a valid {label} folder.")
                    return
        self.run_btn.configure(state="disabled")
        threading.Thread(target=self.run_setup,args=(t,),daemon=True).start()

    # Return Android apps/frontends checked in the UI as one simple list.
    def selected_android_apps(self):
        selected = [n for n,v in self.app_vars.items() if v.get()]
        selected += [n for n,v in self.frontend_vars.items() if v.get()]
        return selected

    # Return normal /switch homebrew apps currently checked.
    def selected_switch_apps(self):
        return [n for n,v in self.switch_vars.items() if v.get()]

    # Return Switch packages that merge files at SD root/Atmosphere level.
    def selected_switch_root_packages(self):
        return [n for n,v in self.switch_root_vars.items() if v.get()]

    # Keep the at-a-glance count honest: selected, already installed, and what will actually be installed.
    def update_summary(self):
        selected_android = self.selected_android_apps()
        selected_switch = self.selected_switch_apps()
        selected_switch_root = self.selected_switch_root_packages()
        profile = self.profile_var.get()
        if profile in ANDROID_PROFILES or profile == "Auto detect":
            installed = sum(1 for name in selected_android if ANDROID_PACKAGES.get(name) in self.installed_packages)
            missing = max(0, len(selected_android) - installed)
            extras = int(self.bios_mode_var.get() != "None") + int(self.romdirs_var.get())
            self.summary_var.set(f"Selected {len(selected_android)} app(s) · Already installed {installed} · Will install {missing} · Extra actions {extras}")
        elif profile == SWITCH_PROFILE:
            actions = len(selected_switch) + len(selected_switch_root)
            actions += int(self.switch_base_var.get())
            actions += int(self.sigpatch_mode_var.get() != "None")
            actions += int(self.firmware_mode_var.get() != "None")
            actions += int(self.bios_mode_var.get() != "None")
            actions += int(self.romdirs_var.get())
            self.summary_var.set(f"Selected {actions} Switch action(s)")
        else:
            actions = int(self.bios_mode_var.get() != "None") + int(self.romdirs_var.get())
            self.summary_var.set(f"Selected {actions} setup action(s)")

    # Read installed Android package IDs and versionNames so HandheldHero can skip pointless reinstalls and label what is already there.
    def scan_installed_android(self, serial):
        try:
            r = adb(["shell","pm","list","packages"],serial=serial,timeout=30)
            packages = set()
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    packages.add(line.split(":",1)[1].strip())
            self.installed_packages = packages
            self.installed_versions = {}
            for display,pkg in ANDROID_PACKAGES.items():
                if pkg in packages:
                    rv = adb(["shell","dumpsys","package",pkg],serial=serial,timeout=12)
                    m = re.search(r"versionName=([^\s]+)", rv.stdout)
                    if m:
                        self.installed_versions[display] = m.group(1)
            # Update checkbox labels after the Android package scan without touching Tk from the worker thread.
            def refresh_labels():
                self.refresh_version_labels()
                self.update_summary()
            self.root.after(0,refresh_labels)
        except Exception as e:
            self.log(f"Installed-app scan warning: {e}")

    # Build the exact human-readable plan used by Dry Run. Run Setup should never be a mystery button.
    def build_plan(self):
        t = self.selected_target()
        if not t:
            return ["No target selected."]
        profile = self.profile_var.get()
        lines = [f"Target: {t['label']}", f"Profile: {profile}", ""]
        if profile in ANDROID_PROFILES:
            selected = self.selected_android_apps()
            if selected:
                lines.append("Android apps:")
                for name in selected:
                    pkg = ANDROID_PACKAGES.get(name)
                    state = "already installed" if pkg in self.installed_packages else "will install"
                    lines.append(f"  - {name}: {state}")
            if self.obtainium_var.get():
                lines.append("  - Obtainium/update JSON: enabled")
        elif profile == SWITCH_PROFILE:
            if self.switch_base_var.get():
                lines.append("- Update/install Switch base: Hekate + Atmosphere + hbmenu/fusee")
            for name in self.selected_switch_root_packages():
                lines.append(f"- Install Switch base extra: {name}")
            for name in self.selected_switch_apps():
                lines.append(f"- Install homebrew: {name}")
            if self.sigpatch_mode_var.get() != "None":
                lines.append(f"- Stage sigpatches from {self.sigpatch_mode_var.get()}: {self.sigpatch_path_var.get()}")
            if self.firmware_mode_var.get() != "None":
                lines.append(f"- Stage firmware from {self.firmware_mode_var.get()}: {self.firmware_path_var.get()}")
        if self.bios_mode_var.get() != "None":
            lines.append(f"- BIOS source: {self.bios_mode_var.get()} — {self.bios_var.get()}")
        if self.romdirs_var.get():
            lines.append("- Create/verify ROM folders")
        if self.backup_var.get():
            lines.append("- Back up supported existing saves/configs before changes")
        if self.verify_var.get():
            lines.append("- Verify after setup")
        return lines

    # Simple reusable read-only popup for plans/update reports.
    def show_text_window(self, title, text):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("760x560")
        box = tk.Text(win,wrap="word")
        box.pack(fill="both",expand=True,padx=10,pady=10)
        box.insert("1.0",text)
        box.configure(state="disabled")
        ttk.Button(win,text="Close",command=win.destroy).pack(pady=(0,10))

    # Show the plan and do absolutely nothing else. This button should always be safe to click.
    def dry_run(self):
        lines = self.build_plan()
        self.show_text_window("Dry Run", "\n".join(lines))

    # Read HandheldHero's tiny Switch version manifest. If an older SD has no manifest, unknown is safer than guessing.
    def read_switch_manifest(self, root):
        root = Path(root)
        p = root / META_DIR_NAME / "switch_versions.json"
        if not p.exists():
            legacy = root / LEGACY_META_DIR_NAME / "switch_versions.json"
            p = legacy if legacy.exists() else p
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    # Merge new version information into the manifest without deleting versions recorded by other install steps.
    def write_switch_manifest(self, root, versions=None, packages=None):
        p = Path(root) / META_DIR_NAME / "switch_versions.json"
        p.parent.mkdir(parents=True,exist_ok=True)
        current = self.read_switch_manifest(root)
        if versions:
            current.update(versions)
        if packages:
            merged = dict(current.get("packages",{}))
            merged.update(packages)
            current["packages"] = merged
        current["updated_at"] = datetime.now().isoformat(timespec="seconds")
        p.write_text(json.dumps(current, indent=2),encoding="utf-8")

    # Force a fresh source-version check and compare it with what the connected device/SD says is installed.
    def check_updates(self):
        t = self.selected_target()
        if not t:
            messagebox.showwarning("Updates","Select a target first.")
            return
        self.update_status_var.set("Checking updates...")
        # Background worker. Network/ADB/disk scans should not freeze the window while Windows thinks about life.
        def work():
            try:
                profile = self.profile_var.get()
                fresh_versions = current_source_versions(force=True)
                self.source_versions = fresh_versions
                self.root.after(0,self.refresh_version_labels)
                lines = []
                if profile == SWITCH_PROFILE:
                    latest = latest_switch_versions()
                    current = self.read_switch_manifest(t["root"])
                    for key,label in [("hekate","Hekate"),("nyx","Nyx"),("atmosphere","Atmosphere"),("hbl","Homebrew Loader"),("hbmenu","hbmenu")]:
                        lat = latest.get(key)
                        if not lat:
                            continue
                        cur = current.get(key,"unknown")
                        status = "current" if cur == lat else ("unknown current version" if cur=="unknown" else "update available")
                        lines.append(f"{label}: installed {cur} · latest {lat} · {status}")
                    installed_packages = current.get("packages",{})
                    chosen = self.selected_switch_root_packages() + self.selected_switch_apps()
                    if chosen:
                        lines.append("")
                        for name in chosen:
                            cur = installed_packages.get(name,"unknown")
                            lat = fresh_versions.get(name,"unknown")
                            status = "current" if cur == lat else ("not installed/tracked" if cur=="unknown" else "update available")
                            lines.append(f"{name}: installed {cur} · latest {lat} · {status}")
                elif profile in ANDROID_PROFILES:
                    lines.append("GitHub-backed Android apps: handled by Obtainium.")
                    custom = []
                    if "RetroArch (AArch64)" in self.selected_android_apps():
                        custom.append(f"RetroArch: installed {self.installed_versions.get('RetroArch (AArch64)','unknown')} · latest source {resolve_retroarch()[1]}")
                    if "Eden (Switch)" in self.selected_android_apps():
                        custom.append(f"Eden: installed {self.installed_versions.get('Eden (Switch)','unknown')} · latest source {resolve_eden()[1]}")
                    if "PPSSPP" in self.selected_android_apps():
                        custom.append(f"PPSSPP: installed {self.installed_versions.get('PPSSPP','unknown')} · latest source {resolve_html_apk('PPSSPP')[1]}")
                    if "Dolphin" in self.selected_android_apps():
                        custom.append(f"Dolphin: installed {self.installed_versions.get('Dolphin','unknown')} · latest source {resolve_html_apk('Dolphin')[1]}")
                    if "DuckStation" in self.selected_android_apps():
                        custom.append(f"DuckStation: installed {self.installed_versions.get('DuckStation','unknown')} · latest source {resolve_html_apk('DuckStation')[1]}")
                    lines.extend(custom or ["No selected non-Obtainium sources to check."])
                else:
                    lines.append("No update checks for this profile yet.")
                msg = "\n".join(lines)
                self.root.after(0,lambda:self.update_status_var.set("Update check complete"))
                self.root.after(0,lambda:self.show_text_window("Update Check",msg))
            except Exception as e:
                self.root.after(0,lambda:self.update_status_var.set("Update check failed"))
                self.root.after(0,lambda err=str(e):messagebox.showerror("Updates",err))
        threading.Thread(target=work,daemon=True).start()

    # Create a timestamped checkpoint of common save/config locations before setup starts changing things.
    def make_backup(self, t, profile):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = BACKUP_DIR / f"{profile.replace('/','-')}-{stamp}"
        base.mkdir(parents=True, exist_ok=True)
        if t["kind"] == "android":
            serial = t["serial"]
            candidates = ["/sdcard/RetroArch/saves","/sdcard/RetroArch/states","/sdcard/PSP/SAVEDATA","/sdcard/Emulation/saves"]
            for remote in candidates:
                if android_exists(serial, remote):
                    self.log(f"Backing up {remote}")
                    adb(["pull",remote,str(base)],serial=serial,timeout=180)
        else:
            root = Path(t["root"])
            for rel in ["Saves","saves",".userdata/shared","RetroArch/.retroarch/config"]:
                src = root / rel
                if src.exists():
                    self.log(f"Backing up {rel}")
                    dst = base / rel.replace("/","_")
                    if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
                    else: shutil.copy2(src,dst)
        self.log(f"Backup checkpoint: {base}")
    # Create conventional ROM folders only; never move/delete the user's ROMs behind their back.
    def create_rom_dirs(self, t, profile):
        if t["kind"] == "android":
            serial = t["serial"]
            for name in ROM_DIRS_ANDROID:
                adb(["shell","mkdir","-p",f"/sdcard/Emulation/ROMs/{name}"],serial=serial,timeout=10)
            self.log("Created /sdcard/Emulation/ROMs folder set")
            return
        root = Path(t["root"])
        if profile == "Modded Switch SD":
            (root/"roms").mkdir(exist_ok=True)
            self.log("Created Switch /roms folder (left otherwise untouched)")
            return
        names = ROM_DIRS_TRIMUI if "TrimUI" in profile else ROM_DIRS_ANDROID
        for name in names:
            (root/"Roms"/name).mkdir(parents=True,exist_ok=True)
        self.log("ROM folders ready")

    # Copy user-supplied BIOS files to the expected locations. ZIPs are extracted safely; nothing copyrighted is downloaded by the app.
    def bios_patch(self, t, profile):
        mode = self.bios_mode_var.get()
        if mode == "None":
            return
        src = Path(self.bios_var.get())
        temp_dir = None
        source_dir = src
        if mode == "Local ZIP":
            temp_dir = Path(tempfile.mkdtemp(prefix="HandheldHero-BIOS-"))
            extract_zip_merge_with_backup(src, temp_dir, temp_dir/"_unused_backup")
            shutil.rmtree(temp_dir/"_unused_backup", ignore_errors=True)
            source_dir = temp_dir
        try:
            if t["kind"] == "android":
                serial = t["serial"]
                targets = ["/sdcard/RetroArch/system","/sdcard/Emulation/BIOS"]
                for remote in targets:
                    adb(["shell","mkdir","-p",remote],serial=serial,timeout=15)
                    r = adb(["push",str(source_dir)+os.sep+".",remote+"/"],serial=serial,timeout=240)
                    if r.returncode != 0:
                        self.log(f"BIOS copy warning for {remote}: {r.stderr.strip()}")
                self.log("BIOS copied to RetroArch/system and Emulation/BIOS")
                return
            root = Path(t["root"])
            if profile == "Modded Switch SD":
                targets = [root/"retroarch"/"cores"/"system"]
            elif "MinUI" in profile:
                targets = [root/"Bios"]
            elif "TrimUI" in profile:
                targets = [root/"BIOS"]
                stock = root/"RetroArch"/".retroarch"/"system"
                if stock.exists(): targets.append(stock)
            else:
                targets = [root/"BIOS"]
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            for dst in targets:
                if mode == "Local ZIP":
                    n = extract_zip_merge_with_backup(src,dst,BACKUP_DIR/f"BIOS-overwrites-{stamp}")
                else:
                    n = copy_tree_with_backup(src,dst,BACKUP_DIR/f"BIOS-overwrites-{stamp}")
                self.log(f"Copied {n} BIOS file(s) to {dst}")
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    # Install/update Obtainium itself from its official GitHub release before handing Android app updates over to it.
    def install_obtainium(self, serial):
        self.log("Installing/updating Obtainium...")
        url,name = github_latest_asset("ImranR98/Obtainium", r"(?i)app-arm64-v8a-release\.apk$")
        apk = download(url, DOWNLOAD_DIR/name)
        r = adb(["install","-r",str(apk)],serial=serial,timeout=180)
        if r.returncode != 0:
            raise RuntimeError("Obtainium install failed: "+(r.stderr or r.stdout).strip())
        self.log("Obtainium installed")

    # Do first-install work for selected Android apps, skip packages already installed, and leave future updates to Obtainium/Play Store.
    def install_android_apps(self, serial, selected, pack_apps):
        by_name = {a.get("name"):a for a in pack_apps}
        results = {}
        for display in selected:
            self.log(f"Resolving {display}...")
            try:
                pkg = ANDROID_PACKAGES.get(display)
                if pkg and pkg in self.installed_packages:
                    results[display] = True
                    self.log(f"{display}: already installed; skipping direct reinstall (Obtainium/Play Store handles updates)")
                    continue
                if display in PLAY_STORE_APPS:
                    pkg = PLAY_STORE_APPS[display]
                    adb(["shell","am","start","-a","android.intent.action.VIEW","-d",f"market://details?id={pkg}"],serial=serial,timeout=15)
                    results[display] = None
                    self.log(f"Opened Play Store page for {display}; tap Install on the handheld")
                    continue
                pack_name = ANDROID_CHOICES[display]
                if pack_name == "__DAIJISHO__":
                    app = daijisho_entry()
                elif pack_name == "__HAKUX__":
                    app = hakux_entry()
                else:
                    app = by_name.get(pack_name)
                if not app:
                    raise RuntimeError("Not found in current Obtainium pack")
                url,name = resolve_from_pack(display,app)
                self.log(f"Downloading {name}")
                apk = download(url, DOWNLOAD_DIR/name)
                r = adb(["install","-r",str(apk)],serial=serial,timeout=240)
                if r.returncode != 0:
                    raise RuntimeError((r.stderr or r.stdout).strip())
                results[display] = True
                self.log(f"Installed {display}")
            except Exception as e:
                results[display] = False
                self.log(f"{display}: direct install skipped/failed ({e}); Obtainium config remains as fallback")
        return results
    # Merge current official Hekate + Atmosphere onto the SD while backing up every file we replace.
    def install_switch_base(self, root):
        root = Path(root)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_root = BACKUP_DIR / f"Switch-base-overwrites-{stamp}"
        self.log("Resolving current Hekate and Atmosphere releases...")

        hek_zip_url, hek_zip_name = github_latest_asset("CTCaer/hekate", r"(?i)_Nyx_.*\.zip$")
        hek_bin_url, hek_bin_name = github_latest_asset("CTCaer/hekate", r"(?i)^hekate_ctcaer_[0-9.]+\.bin$")
        atm_zip_url, atm_zip_name = github_latest_asset("Atmosphere-NX/Atmosphere", r"(?i)^atmosphere-.*\.zip$")
        fusee_url, fusee_name = github_latest_asset("Atmosphere-NX/Atmosphere", r"(?i)^fusee\.bin$")

        hek_zip = download(hek_zip_url, DOWNLOAD_DIR/hek_zip_name)
        hek_bin = download(hek_bin_url, DOWNLOAD_DIR/hek_bin_name)
        atm_zip = download(atm_zip_url, DOWNLOAD_DIR/atm_zip_name)
        fusee = download(fusee_url, DOWNLOAD_DIR/fusee_name)

        atm_count = extract_zip_merge_with_backup(atm_zip, root, backup_root/"Atmosphere")
        hek_count = extract_zip_merge_with_backup(hek_zip, root, backup_root/"Hekate")
        copy_with_backup(hek_bin, root/hek_bin_name, backup_root/"Root")
        copy_with_backup(hek_bin, root/"payload.bin", backup_root/"Root")
        copy_with_backup(fusee, root/"fusee.bin", backup_root/"Root")
        copy_with_backup(fusee, root/"bootloader"/"payloads"/"fusee.bin", backup_root/"BootloaderPayloads")
        (root/"switch").mkdir(parents=True, exist_ok=True)

        self.log(f"Base SD merged: {atm_zip_name} ({atm_count} files)")
        self.log(f"Base SD merged: {hek_zip_name} ({hek_count} files)")
        self.log("Hekate payload also copied as payload.bin; fusee copied to root and bootloader/payloads")
        versions = latest_switch_versions()
        self.write_switch_manifest(root, versions)
        self.log(f"Switch version manifest: Hekate {versions.get('hekate')} · Atmosphere {versions.get('atmosphere')}")
        self.log(f"Overwrite backup: {backup_root}")

    # Keep locally supplied sigpatches staged and visible rather than silently merging an unknown archive into Atmosphere.
    def stage_sigpatch_package(self, root):
        mode = self.sigpatch_mode_var.get()
        if mode == "None":
            return
        src = Path(self.sigpatch_path_var.get())
        stage = Path(root) / META_DIR_NAME / "sigpatches"
        stage.mkdir(parents=True, exist_ok=True)
        if mode == "Local ZIP":
            if not src.is_file() or src.suffix.lower() != ".zip":
                raise RuntimeError("Sigpatch ZIP selection is invalid")
            dst = stage / src.name
            shutil.copy2(src, dst)
            self.log(f"Staged local sigpatch ZIP: {dst}")
        elif mode == "Local folder":
            if not src.is_dir():
                raise RuntimeError("Sigpatch folder selection is invalid")
            dst = stage / src.name
            shutil.copytree(src, dst, dirs_exist_ok=True)
            self.log(f"Staged local sigpatch folder: {dst}")

    # Replace the SD firmware staging folder from a local folder/ZIP, but back up the old folder first.
    def stage_firmware(self, root):
        mode = self.firmware_mode_var.get()
        if mode == "None":
            return
        raw = self.firmware_path_var.get().strip()
        src = Path(raw)
        if not src.exists():
            raise RuntimeError("Firmware source path does not exist")
        root = Path(root)
        dest = root / "firmware"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / f"Switch-firmware-{stamp}"
        if dest.exists():
            shutil.copytree(dest, backup, dirs_exist_ok=True)
            shutil.rmtree(dest)
            self.log(f"Backed up existing firmware folder: {backup}")
        dest.mkdir(parents=True, exist_ok=True)
        if mode == "Local folder":
            for item in src.iterdir():
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
        elif mode == "Local ZIP":
            with zipfile.ZipFile(src) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    rel = Path(info.filename)
                    if rel.is_absolute() or ".." in rel.parts:
                        continue
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as s, open(target, "wb") as d:
                        shutil.copyfileobj(s, d)
        else:
            raise RuntimeError("Firmware source must be a folder or ZIP")
        self.log(f"Firmware staged to: {dest}")

    # Install selected root-level Switch extras from their official GitHub releases and record the installed version.
    def install_switch_root_packages(self, root):
        root = Path(root)
        for display in self.selected_switch_root_packages():
            repo,pattern = SWITCH_ROOT_PACKAGES[display]
            try:
                url,name = github_latest_asset(repo,pattern)
                path = download(url, DOWNLOAD_DIR/name)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup = BACKUP_DIR / f"Switch-{re.sub(r'[^A-Za-z0-9._-]+','_',display)}-{stamp}"
                if path.suffix.lower() != ".zip":
                    raise RuntimeError("Expected ZIP package")
                count = extract_zip_merge_with_backup(path, root, backup, skip_top_level={"README.md","README.txt"})
                version = self.source_versions.get(display)
                if not version or version == "unknown":
                    version = clean_version(github_latest_release(repo).get("tag_name"))
                self.write_switch_manifest(root, packages={display:version})
                self.log(f"Installed Switch base extra: {display} v{version} ({count} files)")
            except Exception as e:
                self.log(f"Switch base extra {display} failed: {e}")

    # Install ordinary NRO homebrew under /switch and track the version in HandheldHero's manifest.
    def install_switch_apps(self, root):
        root = Path(root)
        for display in self.selected_switch_apps():
            repo,pattern = SWITCH_APPS[display]
            try:
                url,name = github_latest_asset(repo,pattern)
                path = download(url, DOWNLOAD_DIR/name)
                appdir = root/"switch"/re.sub(r"[^A-Za-z0-9._-]+","_",display)
                appdir.mkdir(parents=True,exist_ok=True)
                if path.suffix.lower()==".nro":
                    shutil.copy2(path,appdir/path.name)
                elif path.suffix.lower()==".zip":
                    with zipfile.ZipFile(path) as z:
                        for member in z.namelist():
                            if member.lower().endswith(".nro"):
                                data = z.read(member)
                                (appdir/Path(member).name).write_bytes(data)
                version = self.source_versions.get(display)
                if not version or version == "unknown":
                    version = clean_version(github_latest_release(repo).get("tag_name"))
                self.write_switch_manifest(root, packages={display:version})
                self.log(f"Installed Switch homebrew: {display} v{version}")
            except Exception as e:
                self.log(f"Switch app {display} failed: {e}")

    # Do cheap sanity checks after setup so the log says what actually landed instead of declaring victory blindly.
    def verify(self, t, profile, selected):
        if t["kind"] == "android":
            serial = t["serial"]
            r = adb(["shell","getprop","ro.product.model"],serial=serial,timeout=10)
            if r.returncode == 0:
                self.log(f"ADB verification OK: {r.stdout.strip()}")
            if self.obtainium_var.get():
                r = adb(["shell","ls","/sdcard/Download/HandheldHero-Obtainium.json"],serial=serial,timeout=10)
                self.log("Obtainium JSON verified on device" if r.returncode==0 else "Obtainium JSON not found on device")
            for display in selected:
                pkg = ANDROID_PACKAGES.get(display)
                if pkg:
                    r = adb(["shell","pm","path",pkg],serial=serial,timeout=10)
                    self.log(f"{display}: {'installed' if r.returncode==0 and 'package:' in r.stdout else 'not detected'}")
        else:
            root = Path(t["root"])
            self.log(f"Storage verification OK: {root} ({profile})")
            if profile == SWITCH_PROFILE and self.switch_base_var.get():
                required = [root/"atmosphere", root/"bootloader", root/"hbmenu.nro", root/"payload.bin"]
                missing = [p.name for p in required if not p.exists()]
                if missing:
                    self.log("Switch base verification missing: " + ", ".join(missing))
                else:
                    self.log("Switch base verification OK: Atmosphere, Hekate bootloader, hbmenu, and payload.bin present")
            if profile == SWITCH_PROFILE and self.firmware_mode_var.get() != "None":
                fw = root/"firmware"
                self.log("Firmware staging verified" if fw.exists() and any(fw.rglob("*")) else "Firmware staging not found")
            if profile == SWITCH_PROFILE and self.sigpatch_mode_var.get() != "None":
                sp = root / META_DIR_NAME / "sigpatches"
                self.log("Sigpatch package staging verified" if sp.exists() and any(sp.rglob("*")) else "Sigpatch staging not found")

    # Orchestrate the checked actions in a predictable order: backup, folders/BIOS, platform installs, then verification.
    def run_setup(self, t):
        try:
            profile = self.profile_var.get()
            if profile == "Auto detect":
                profile = classify_android(t["serial"]) if t["kind"]=="android" else classify_drive(t["root"])
            self.log(f"Starting setup for {profile}")
            selected = self.selected_android_apps()
            if self.backup_var.get():
                self.make_backup(t,profile)
            if self.romdirs_var.get():
                self.create_rom_dirs(t,profile)
            if self.bios_mode_var.get() != "None":
                self.bios_patch(t,profile)

            if t["kind"]=="android":
                serial = t["serial"]
                pack_path,pack_apps = build_filtered_pack(selected)
                if self.obtainium_var.get():
                    self.install_obtainium(serial)
                    adb(["push",str(pack_path),"/sdcard/Download/HandheldHero-Obtainium.json"],serial=serial,timeout=60)
                    self.log("Pushed filtered Obtainium update JSON to Downloads")
                if self.install_now_var.get() and selected:
                    self.install_android_apps(serial,selected,pack_apps)
                if self.obtainium_var.get():
                    adb(["shell","monkey","-p","dev.imranr.obtainium","1"],serial=serial,timeout=15)
                    self.log("Opened Obtainium. Import HandheldHero-Obtainium.json from Downloads once.")
            elif profile == "Modded Switch SD":
                if self.switch_base_var.get():
                    self.install_switch_base(t["root"])
                self.install_switch_root_packages(t["root"])
                if self.sigpatch_mode_var.get() != "None":
                    self.stage_sigpatch_package(t["root"])
                if self.firmware_mode_var.get() != "None":
                    self.stage_firmware(t["root"])
                self.install_switch_apps(t["root"])

            if self.verify_var.get():
                self.verify(t,profile,selected)
            self.log("SETUP COMPLETE")
            self.root.after(0,lambda:messagebox.showinfo(APP_NAME,"Setup finished. Check the log for anything that needs one manual tap."))
        except Exception as e:
            self.log(f"ERROR: {e}")
            self.root.after(0,lambda err=str(e):messagebox.showerror(APP_NAME,f"Setup stopped:\n{err}"))
        finally:
            self.root.after(0,lambda:self.run_btn.configure(state="normal"))

# Start Tk with the native-looking Windows theme when available, then hand control to HandheldHero.
def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    HandheldHeroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
