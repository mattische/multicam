# Packaging notes: AUR package and Omarchy plugin

This folder holds two things that ship multicam outside of `install.sh`:

| Path | What |
|---|---|
| `aur/PKGBUILD`, `aur/.SRCINFO` | AUR package `multicam` (system-wide install with pacman/yay) |
| `omarchy-plugin/` | A complete Omarchy bar plugin `io.github.mattische.multicam`, to be published as its own repository |

Everything below was checked against Omarchy 4.0.4 (`/usr/share/omarchy`, Quattro shell) on this machine.

## Status: B1-B9 are implemented (multicam 1.4.0)

Section 2 below is the original plan. What was actually done, where it differs:

- **B1** `INSTALL_MODE` = `package` (program under `/usr`, or any `<prefix>/bin` with `<prefix>/share/multicam/lib/bg.py`
  next to it), `user` (`~/.local/share/multicam`, install.sh) or `repo` (git checkout, behaves like `user`).
  `SHARE_DIR` holds `lib/bg.py` and `shell-plugin/`; install.sh now also copies `shell-plugin/` into
  `~/.local/share/multicam/`. `multicam check-bgremove` prints the resolved `bg.py` path.
- **B2/B3** as planned (`latest_tag`, `PKG_UPDATE_CMD='yay -Syu multicam'`); the green line and `U` show the new
  version and the yay command. Pre-release tags (`v2.0.0-rc1`) are ignored.
- **B4** `cmd_uninstall` removes the same per-user items in every mode (it never touches the program in `/usr`) and
  in package mode ends with `sudo pacman -Rns multicam`.
- **B5** `shell-plugin/` **is** the new plugin and the single source; `packaging/omarchy-plugin/` is an identical copy
  for the separate plugin repository (tests/run.py T-A1 fails if they differ). `showWhenIdle` defaults to **false**
  (icon only while recording, as before); the plugin README explains `omarchy bar set ... showWhenIdle true --json`.
  `multicam setup-bar [--remove]` only copies the shipped files (no `omarchy plugin add` / network), rescans and
  enables; it disables + deletes only `~/.config/omarchy/plugins/multicam.recording`. A git checkout of the plugin
  (`omarchy plugin add`) is left alone. The choice is remembered as `BAR_PLUGIN=on|off` in `~/.config/multicam/config`
  (not a marker file); package mode runs it once at the first TUI start when `BAR_PLUGIN` is unset and
  `BAR_INDICATOR=on`, and refreshes a plain copy whose files differ from `/usr/share/multicam/shell-plugin`.
  Safety: enable/disable/rescan go to the running shell, which reads the **real** home's plugin folder, so they are
  skipped when `$HOME` is not the user's passwd home (tests, scratch copies); the command then prints the enable command.
- **B6** `multicam setup-keybind [--remove]`; user mode writes the full `~/.local/bin/multicam` path (as before),
  package mode plain `multicam`.
- **B7** `Icon=multicam` in the template; install.sh installs `~/.local/share/icons/hicolor/scalable/apps/multicam.svg`,
  uninstall removes it (and the icon folders if they are empty afterwards).
- **B8** the TUI requires `omarchy-capture-screenrecording`, `omarchy-capture-region`, `omarchy-launch-tui`
  ("multicam needs Omarchy (https://omarchy.org): ... is missing"); install.sh refuses when `pacman -Q multicam`
  succeeds; when both `~/.local/bin/multicam` and `/usr/bin/multicam` exist the form shows how to remove the per-user
  program files (settings and add-on are kept, the package uses them too).
- **B9** `.gitattributes` export-ignores `tests/`, `docs/test-evidence/`, `docs/prototypes/`, `packaging/`;
  PKGBUILD is at 1.4.0 with `.SRCINFO` regenerated. `LICENSE`, `assets/` and the new `shell-plugin/` files must be
  committed before tagging v1.4.0.

## 1. How the pieces relate

- **multicam (the app)** is the bash TUI + `lib/bg.py`. It does the recording. Install it per user with
  `install.sh` (as today) or system-wide from the AUR (`yay -S multicam`).
- **The bar plugin** is only a button in the Omarchy bar. Idle: a record icon that opens the TUI
  (`omarchy-launch-tui --app-id=TUI.float multicam`). Recording: blinking red icon + elapsed time, click runs
  `multicam stop`. It reads `$XDG_RUNTIME_DIR/multicam/recording`, which the app writes. Without the app it shows
  a dimmed icon whose click opens the GitHub page. The plugin never installs the app.
- **Omarchy** itself is required at runtime (`omarchy-capture-screenrecording`, `omarchy-launch-tui`,
  `omarchy-capture-region`, `omarchy-capture-webcam-list`, `omarchy-shell`). On this system they come from the
  `omarchy` package in Omarchy's own pacman repository (`[omarchy]`, also home of `omacut`). That repository is
  neither official Arch nor AUR, so an AUR package must not list `omarchy` in `depends=()` (users without that
  repo could never resolve it). `omacut` is only mentioned in `optdepends` (optdepends are never auto-installed).
  The app already checks for `omarchy-capture-screenrecording` at start; see change B8 for the rest.

### Facts about `omarchy plugin add` (read from `/usr/bin/omarchy-plugin-add`, `-update`, `-validate`)

- It runs `git clone -- "$url" ~/.config/omarchy/plugins/.add.tmp.$$`, validates **the repository root**
  (`$stage/manifest.json`), then moves the whole checkout to `~/.config/omarchy/plugins/<manifest id>/`.
- There is **no subdirectory, branch or ref option**. `omarchy plugin update` does `git fetch origin HEAD` and a
  fast-forward merge of the default branch, then re-validates (rolls back on failure).
- The publishing guide (plugins.omarchy.org/publish.html) requires a public GitHub repo with `manifest.json` in the
  repository root, a README and a license. Listing in the marketplace: issue form at
  https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml
- Validation refuses ids under `omarchy.*` and any symlink in the folder (`.git` excepted).

### Recommended repository layout

Use a **separate public repository `mattische/omarchy-multicam-plugin`** whose root is the content of
`packaging/omarchy-plugin/` (manifest.json, BarWidget.qml, README.md, LICENSE). This is the same pattern as
Basecamp's `basecamp/omarchy-hey-plugin` (installed here as `37signals.hey`).

Putting `manifest.json` at the root of `mattische/multicam` would technically work, but then every user's plugin
folder would be a full clone of the app (bin/, tests/, docs/ images...) inside the trusted shell plugin directory,
every app commit would show up as a plugin update, and the app repo root would be dictated by the shell. A
subdirectory is not supported at all. Keep the source of truth in this repo (`packaging/omarchy-plugin/`, or move
it to `shell-plugin/`) and copy it to the plugin repo on release (manually or with a small GitHub Action /
`git subtree split --prefix=packaging/omarchy-plugin`).

Install for users:

```
yay -S multicam            # or: curl -fsSL .../install.sh | bash
omarchy plugin add https://github.com/mattische/omarchy-multicam-plugin.git --enable
```

### The plugin vs. today's `shell-plugin/` (`multicam.recording`)

| | `shell-plugin/` (today) | `packaging/omarchy-plugin/` (new) |
|---|---|---|
| id | `multicam.recording` (not namespaced) | `io.github.mattische.multicam` |
| idle | hidden | record icon, click opens the TUI (setting `showWhenIdle`, default on) |
| recording | blinking red + time, click stops | same |
| stop command | `$HOME/.local/bin/multicam stop` (breaks for /usr/bin) | `PATH="$PATH:$HOME/.local/bin" multicam stop` |
| app missing | n/a | dimmed icon, click opens the GitHub page |

Both must not be enabled at the same time (two icons). See B5 for the migration.

## 2. Changes needed in `bin/multicam` for a system (pacman) install

Line numbers refer to bin/multicam as of 1.3.0.

### B1. Find `lib/bg.py` and the plugin files under `/usr/share/multicam`

Today `APPDIR=${SELF%/*/*}` (line 7). For `/usr/bin/multicam` that is `/usr`, so `$APPDIR/lib/bg.py` (line 634)
would point to `/usr/lib/bg.py`, which does not exist. Replace with:

```bash
SELF=$(readlink -f "${BASH_SOURCE[0]}")
APPDIR=${SELF%/*/*}
if [[ -f $APPDIR/lib/bg.py ]]; then               # git checkout, or ~/.local/share/multicam (install.sh)
  SHARE_DIR=$APPDIR
elif [[ -f $APPDIR/share/multicam/lib/bg.py ]]; then  # /usr/bin/multicam -> /usr/share/multicam (package)
  SHARE_DIR=$APPDIR/share/multicam
else
  SHARE_DIR=$APPDIR
fi
# package = installed by pacman; user = install.sh (or a git checkout)
if [[ $SELF == /usr/* ]]; then INSTALL_MODE=package; else INSTALL_MODE=user; fi
```

and use `"$SHARE_DIR/lib/bg.py"` in `launch_cam` (line 634) and `"$SHARE_DIR/shell-plugin"` wherever plugin
files are copied. `DATA_DIR=$HOME/.local/share/multicam` stays: in package mode it only holds the per-user
background-removal add-on (`bg/`), which keeps working unchanged (venv + model are per user, never in /usr).

### B2. `multicam update` refuses in package mode

```bash
cmd_update() {
  if [[ $INSTALL_MODE == package ]]; then
    _ 'multicam was installed with pacman. Update it with your AUR helper, e.g.:  yay -Syu multicam\n' >&2
    return 1
  fi
  ... unchanged ...
}
```

`update_flow` (the `U` key, line 1177) must not call `cmd_update` in package mode; show the same text in `MSG`
instead.

### B3. Update check in package mode compares release tags, not `origin/main`

`update_available` (line 244) returns 1 without `$REV_FILE`, so a packaged copy would never see updates. Add:

```bash
latest_tag() { # newest vX.Y.Z tag of the public repo, without the v
  GIT_TERMINAL_PROMPT=0 timeout 10 git ls-remote --tags --refs "$DEFAULT_SRC" 'v*' 2>/dev/null |
    sed -n 's|.*refs/tags/v||p' | sort -V | tail -n1
}
update_available() { # 0 = a new version exists
  local cur new
  need git || return 1
  if [[ $INSTALL_MODE == package ]]; then
    new=$(latest_tag)
    [[ -n $new && $new != "$VERSION" && $(printf '%s\n%s\n' "$VERSION" "$new" | sort -V | tail -n1) == "$new" ]]
    return
  fi
  [[ -s $REV_FILE ]] || return 1
  cur=$(<"$REV_FILE"); new=$(latest_rev)
  [[ -n $new && $new != "$cur" ]]
}
```

The green "update available" line in the form should then say "update with: yay -Syu multicam" in package mode.
(The AUR package may lag behind the tag by a few hours; that is fine.)

### B4. `multicam uninstall` in package mode removes only per-user data, then points to pacman

pacman cannot remove files in home directories. In package mode `cmd_uninstall` (line 157) should list and remove
only: `$CONF_DIR`, `$DATA_DIR` (the add-on), the bar plugin folder, the keybind line, and a stray
`~/.local/share/applications/multicam.desktop` if one exists; it must **not** touch `/usr/bin/multicam`. Then:

```bash
if [[ $INSTALL_MODE == package ]]; then
  _ 'Per-user files removed. Remove the program itself with:  sudo pacman -Rns multicam\n'
fi
```

`uninstall.sh` keeps working (it calls `bin/multicam uninstall` from the checkout = user mode).

### B5. Per-user bar plugin setup: `multicam setup-bar [--remove]`

A package cannot write to `~/.config/omarchy/plugins`. Add a command (and call it from install.sh instead of the
inline copy in install.sh, ~lines 90-106, so both install paths share one implementation):

```bash
PLUGIN_ID=io.github.mattische.multicam
PLUGIN_DIR=$HOME/.config/omarchy/plugins/$PLUGIN_ID
PLUGIN_REPO=https://github.com/mattische/omarchy-multicam-plugin.git
OLD_PLUGIN_ID=multicam.recording

cmd_setup_bar() { # [--remove] [--copy]
  local a remove=0 copy=0
  for a in "$@"; do case $a in --remove) remove=1 ;; --copy) copy=1 ;; esac; done
  need omarchy && need omarchy-shell || { _ 'Omarchy shell not found - no bar plugin.\n' >&2; return 1; }
  # migrate the old, non-namespaced plugin (it would show a second icon)
  if [[ -d $HOME/.config/omarchy/plugins/$OLD_PLUGIN_ID ]]; then
    timeout 5 omarchy plugin disable "$OLD_PLUGIN_ID" >/dev/null 2>&1
    rm -rf "$HOME/.config/omarchy/plugins/$OLD_PLUGIN_ID"
  fi
  if ((remove)); then
    [[ -d $PLUGIN_DIR ]] && timeout 10 omarchy plugin remove "$PLUGIN_ID" --yes >/dev/null 2>&1
    rm -rf "$PLUGIN_DIR"; : >"$CONF_DIR/bar-plugin-removed"
    timeout 5 omarchy-shell shell rescanPlugins >/dev/null 2>&1
    _ 'Bar plugin removed.\n'; return 0
  fi
  rm -f "$CONF_DIR/bar-plugin-removed"
  [[ -d $PLUGIN_DIR ]] && { _ 'The bar plugin is already installed (%s).\n' "$PLUGIN_DIR"; return 0; }
  # preferred: a git-managed checkout, so 'omarchy plugin update' keeps it current
  if ((!copy)) && need git &&
    timeout 60 omarchy plugin add "$PLUGIN_REPO" --enable --yes >/dev/null 2>&1; then
    _ 'Bar plugin installed and enabled.\n'; return 0
  fi
  # fallback (offline, private repo): copy the files shipped with the app
  mkdir -p "$PLUGIN_DIR" && cp -- "$SHARE_DIR"/shell-plugin/* "$PLUGIN_DIR"/ || return 1
  timeout 5 omarchy-shell shell rescanPlugins >/dev/null 2>&1
  timeout 10 omarchy plugin enable "$PLUGIN_ID" >/dev/null 2>&1 ||
    { _ 'Installed in %s; enable with: omarchy plugin enable %s\n' "$PLUGIN_DIR" "$PLUGIN_ID"; return 0; }
  _ 'Bar plugin installed and enabled.\n'
}
```

Dispatcher (line 276): `setup-bar) shift; cmd_setup_bar "$@"; exit $? ;;` and a line in `usage`.

First run in package mode (in `main`, after `load_config`): install the plugin once, unless the user removed it.

```bash
if [[ $INSTALL_MODE == package && ! -d $PLUGIN_DIR && ! -e $CONF_DIR/bar-plugin-removed ]] && need omarchy-shell; then
  cmd_setup_bar >/dev/null 2>&1 &
fi
```

If the plugin folder is a plain copy (no `.git`) and the packaged files are newer, refresh it:
`[[ -d $PLUGIN_DIR && ! -d $PLUGIN_DIR/.git ]] && ! diff -q "$SHARE_DIR/shell-plugin" "$PLUGIN_DIR" >/dev/null 2>&1 && cp -- "$SHARE_DIR"/shell-plugin/* "$PLUGIN_DIR"/`
(Saving under `~/.config/omarchy/plugins` hot-reloads automatically.)

For this, `shell-plugin/` in the repo should become the new plugin: replace `Recording.qml` + the old manifest with
`packaging/omarchy-plugin/{manifest.json,BarWidget.qml}` (and change the `$HOME/.local/bin/multicam stop` in any
QML that stays to the PATH form above). The comment in bin/multicam line 812 ("bar-pluginet multicam.recording")
and `cmd_uninstall`'s `omarchy plugin disable "$PLUGIN_ID"` then use the new id automatically.

### B6. Keybind: move it into the app (`multicam setup-keybind [--remove]`)

install.sh writes `omarchy-launch-tui --app-id=TUI.float $HOME/.local/bin/multicam`. A package user has no
installer to answer that question. Move the keybind block in install.sh (the `kb == ask` question and the `bindings.lua` append, ~lines 70-88) into `cmd_setup_keybind` in bin/multicam
and write the command as `omarchy-launch-tui --app-id=TUI.float multicam` (works for both modes, because
`~/.local/bin` and `/usr/bin` are both on Omarchy's PATH). install.sh then calls `"$BIN" setup-keybind`.
`cmd_uninstall` already removes the line by its `-- multicam` suffix.

### B7. Desktop entry and icon

- Template `multicam.desktop`: change `Icon=camera-video` to `Icon=multicam` (the PKGBUILD rewrites it anyway).
  Exec stays `omarchy-launch-tui --app-id=TUI.float @BIN@`; install.sh substitutes `~/.local/bin/multicam`, the
  PKGBUILD substitutes plain `multicam`.
- install.sh: also `install -Dm644 assets/multicam.svg ~/.local/share/icons/hicolor/scalable/apps/multicam.svg`
  and remove it in `cmd_uninstall` (user mode).

### B8. Startup checks and double installs

- `main` (line 1571): also require `omarchy-launch-tui` and `omarchy-capture-region` (they are not package deps),
  with the message "multicam needs Omarchy (https://omarchy.org)".
- Package mode: if `~/.local/bin/multicam` also exists, it shadows `/usr/bin/multicam` on PATH. Warn once:
  "An older per-user copy exists in ~/.local/bin; remove it with ~/.local/share/multicam/bin/multicam uninstall".
- install.sh: if `pacman -Qq multicam` succeeds, refuse (or ask) with "multicam is installed as a package; use
  yay -Syu multicam".

### B9. Release tarball contents

`LICENSE` and `assets/` are currently **untracked**. They must be committed before tagging, otherwise
`package()` fails (`install: cannot stat 'LICENSE'` / `assets/multicam.svg`). Optional: a `.gitattributes` with
`tests/ export-ignore`, `docs/test-evidence/ export-ignore`, `packaging/ export-ignore` keeps the GitHub tarball
small (the PKGBUILD needs only `bin/`, `lib/`, `shell-plugin/`, `assets/`, `multicam.desktop`, `README.md`, `LICENSE`).

## 3. Validation done

- `omarchy plugin validate` on a scratch copy of the current `shell-plugin/`: exit 0.
- `omarchy plugin validate packaging/omarchy-plugin`: exit 0.
- qmllint: `/usr/bin/qmllint` is the Qt 5 one (qt5-declarative) and is useless here. Use
  `/usr/lib/qt6/bin/qmllint -I "$OMARCHY_PATH/shell" BarWidget.qml`: exit 0, warnings only, all caused by qmllint
  not resolving the shell's `qs.Ui` module outside the shell (the current Recording.qml gets the same warnings).
  The extra "BarWidget -> BarWidget inheritance cycle" warning comes from the file being named like its base type,
  exactly as in Omarchy's own plugin tutorial; at runtime `qs.Ui.BarWidget` wins.
- Runtime: loaded `BarWidget.qml` in a separate offscreen Quickshell instance with copies of the shell's
  `Commons/` and `Ui/` (live shell untouched): no QML errors; idle -> `recording=false installed=true` (27 px icon);
  with a state file 75 s old -> `recording=true elapsed=01:17`; with `PATH=/usr/bin` -> `installed=false`.
- AUR: `makepkg -f` in a scratch dir with a local tarball (`git archive HEAD` + the uncommitted LICENSE and
  assets): package built; contents `/usr/bin/multicam`, `/usr/share/multicam/{lib/bg.py,shell-plugin/*}`,
  `/usr/share/applications/multicam.desktop` (Exec=`omarchy-launch-tui --app-id=TUI.float multicam`,
  Icon=`multicam`; `desktop-file-validate` ok), `/usr/share/icons/hicolor/scalable/apps/multicam.svg`,
  `/usr/share/doc/multicam/README.md`, `/usr/share/licenses/multicam/LICENSE`. `.SRCINFO` from
  `makepkg --printsrcinfo`. **namcap is not installed** (`sudo pacman -S namcap`, then
  `namcap PKGBUILD multicam-*.pkg.tar.zst`). The package was not installed.

### Dependency names (checked with `pacman -Qo` / `pacman -Si`)

| Command | Package | Repo |
|---|---|---|
| hyprctl | `hyprland` | extra |
| jq | `jq` | extra |
| mpv | `mpv` | extra |
| pactl | `libpulse` | extra |
| gpu-screen-recorder | `gpu-screen-recorder` | extra (also an older build in [omarchy]) |
| v4l2-ctl (opt) | `v4l-utils` | extra |
| hyprpicker (opt) | `hyprpicker` | extra |
| python3, ffmpeg, curl (opt, add-on) | `python`, `ffmpeg`, `curl` | core/extra |
| git (opt, update check) | `git` | extra |
| omacut (opt) | `omacut` | [omarchy] only |
| omarchy-* scripts | `omarchy` | [omarchy] only - cannot be a dependency |

`grim` is not used by bin/multicam (only by tests/), so it is not in optdepends; install.sh's "optional: grim"
note can go too. The AUR RPC returned no package named `multicam`, `omarchy` or `omacut`.

## 4. Publishing

### GitHub tag and release (needs the repo public, otherwise the tarball URL is 404 for everyone)

```
# bump VERSION= in bin/multicam if needed, commit LICENSE + assets/ (B9), push main
git tag -a v1.3.0 -m "multicam 1.3.0"
git push origin v1.3.0
gh release create v1.3.0 --title "multicam 1.3.0" --generate-notes
```

### AUR (first time)

1. Create an account at https://aur.archlinux.org/register.
2. SSH key just for the AUR: `ssh-keygen -t ed25519 -f ~/.ssh/aur`, paste `~/.ssh/aur.pub` into
   "My Account" -> "SSH Public Key", and add to `~/.ssh/config`:
   ```
   Host aur.archlinux.org
     IdentityFile ~/.ssh/aur
     User aur
   ```
3. `git clone ssh://aur@aur.archlinux.org/multicam.git ~/aur/multicam` (warns about an empty repository; that is
   how a new package is created).
4. `cp packaging/aur/PKGBUILD ~/aur/multicam/ && cd ~/aur/multicam`, put your contact in the `# Maintainer:` line.
5. Replace `SKIP` with the real checksum: `updpkgsums` (package `pacman-contrib`), then
   `makepkg --printsrcinfo > .SRCINFO`.
6. Test: `makepkg -si` (or in a clean chroot: `pkgctl build` from `devtools`), `namcap PKGBUILD *.pkg.tar.zst`.
7. `git add PKGBUILD .SRCINFO && git commit -m "Initial import: multicam 1.3.0" && git push` (the AUR only
   accepts the `master` branch; do not commit built packages or the tarball).

### AUR (each release)

Tag + release on GitHub, then in `~/aur/multicam`: set `pkgver`, reset `pkgrel=1`, `updpkgsums`,
`makepkg --printsrcinfo > .SRCINFO`, test build, commit, push.

### Omarchy plugin

1. Create the public repo `mattische/omarchy-multicam-plugin`; copy `packaging/omarchy-plugin/*` into its root
   (manifest.json, BarWidget.qml, README.md, LICENSE); push.
2. Test on a machine: `omarchy plugin remove multicam.recording` (old plugin), then
   `omarchy plugin add https://github.com/mattische/omarchy-multicam-plugin.git --enable`.
3. For each plugin change bump `"version"` in manifest.json; users get it with `omarchy plugin update`.
4. Optional: list it in the marketplace via
   https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml (a preview image
   helps).
