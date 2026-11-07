# Cross-device integration checklist

## Root cause found on the development device

The working desktop was using a different implementation from this repository:

- An independent `qs -c launchpad` process and a private `~/.local/bin/launchpad` script.
- User Hyprland pinch callbacks invoking that private script.
- A saved Dock Applications pin invoking an absolute path to the same script.
- No registered `okuma.dev_launchpad4omarchy` plugin (its IPC status was `unknown`).

Installing the plugin source on another device cannot reproduce those unshipped files.
Separately, older OkumarchyDock defaults targeted `omarchy.menu`, not Launchpad.
Neither observation establishes a touchpad hardware defect.

Live installation also exposed asynchronous plugin discovery: `rescanPlugins` can
return before a new plugin appears in the registry. Enabling/loading can interrupt
an IPC reply after successfully saving the setting. The installer now waits for
registry discovery and verifies the actual panel status rather than trusting the
command exit status alone.

## Required deployment

1. Deploy the updated source of **both** projects. Updating only Launchpad does not
   change the Applications routing in an older installed Dock. For Git-managed
   installations use `omarchy plugin update` after the fixes are published. Local
   snapshot installations need a reviewed source update; `install.sh` intentionally
   does not overwrite an existing target.
2. Enable OkumarchyDock. Keep Omarchy's built-in dock enabled for floating workspaces.
3. On each device run the updated Launchpad `install.sh`. It enables the plugin,
   installs gestures, reloads Hyprland, and verifies the managed block actually ran.
4. If migrating the standalone version, back up the user configs and remove only
   the old pinch callbacks and standalone autostart first. See [integration.md](integration.md).
5. If the running shell still reports old Dock status after a source update, restart
   it deliberately with `omarchy restart shell`. Some shells retain cached QML across
   plugin rescans. The installer never forces this shared-process restart.

## Acceptance checks on every device

```bash
omarchy-shell shell call okuma.dev_launchpad4omarchy status ''
omarchy-shell shell call okuma.dev_dock4omarchy status ''
python3 ~/.config/omarchy/plugins/okuma.dev_launchpad4omarchy/doctor.py
hyprctl configerrors
```

- Launchpad status must be `open` or `closed`.
- Dock status must contain `launcherPlugin`, normally `auto`.
- The doctor's exact managed-block check must return `ok`.
- Hyprland must report no configuration errors.
- Click Applications: the grid opens. After closing with Escape, click again.
- Four-finger pinch inward opens; outward closes. Three-finger outward is also a
  close fallback, unless dragging takes precedence.
- Verify two-finger grid scrolling and existing workspace/bar gestures separately.
- Test again after logout/login and reboot. One live-session test does not prove
  startup behavior on every device.

If IPC works but physical four-finger pinch does not, check the touchpad's libinput
recognition and try `install.sh --fingers 3` if appropriate. That deliberately changes
the finger-count profile and may conflict with three-finger dragging. No software
change can guarantee four-finger gestures on hardware/firmware that cannot report
them. Do not copy the development machine's touchpad preferences or grant raw input
permissions merely to make installation appear successful.

The new paths need no private script or standalone process. Personal input settings,
workspace swipes, and bar gestures are preserved. Other third-party docks need their
own explicit Applications command configuration; automatic selection here is an
OkumarchyDock feature, not a compositor-wide launcher override.
