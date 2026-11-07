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

The reference machine also had a manual four-finger horizontal workspace binding,
plus options to visit empty numeric workspaces. Previous releases shipped neither:
working pinch/Dock integration therefore did not imply working workspace swipes.
Workspace switching is a compositor configuration issue, independent of the Dock.

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
2. Enable OkumarchyDock if desired. The Launchpad installer replaces the stock Dock
   with a managed user-owned clone for floating workspaces; do not enable both copies.
   An originally disabled stock Dock stays disabled through its disabled adapter.
3. On each device run the updated Launchpad `install.sh`. It enables the plugin,
   installs pinch and workspace gestures, reloads Hyprland, and verifies both managed
   blocks actually ran. Existing manual four-finger horizontal bindings must be
   reviewed/migrated first, or preserved with `install.sh --no-workspaces`.
   Gesture-only setup requires `setup-gestures.py install --workspaces` explicitly.
   The full installer also adapts the built-in Dock, selects strict Launchpad routing
   in an already-installed OkumaDock using `auto` and creates the `Okuma Launchpad`
   desktop entry. Explicit alternative launcher preferences remain unchanged.
   Use `--no-dock-integration` to preserve existing Dock routing instead.
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
- OkumaDock status must contain `launcherPlugin`: `okuma.dev_launchpad4omarchy` after
  full Launchpad integration; `auto` is OkumaDock's own fallback-capable default.
- `omarchy-shell omarchy.dock launchpadIntegration` must return `okuma-launchpad-v1`
  when the stock-Dock adapter is installed and enabled.
- The doctor's exact pinch and workspace managed-block checks must return `ok`
  (or workspace gestures must be intentionally maintained manually).
- Hyprland must report no configuration errors.
- Click Applications on each installed Dock: this project's grid must open, not the
  stock AppGrid/menu. Test `omarchy-shell omarchy.dock apps` and the generated desktop
  entry as well. After closing with Escape, click again.
- Four-finger pinch inward opens; outward closes. Three-finger outward is also a
  close fallback, unless dragging takes precedence.
- Close Launchpad, release modifiers, then slide four fingers horizontally in both
  directions. Verify continuous motion and release-to-commit, including entry into
  an empty numeric neighbor. Very short swipes may cancel normally.
- Verify two-finger grid scrolling, three-finger dragging and vertical bar gestures
  remain unchanged. Test multi-monitor behavior on the target device if applicable.
- Test again after logout/login and reboot. One live-session test does not prove
  startup behavior on every device.

If IPC works but physical four-finger pinch does not, check the touchpad's libinput
recognition and try `install.sh --fingers 3` if appropriate. That deliberately changes
the finger-count profile and may conflict with three-finger dragging. No software
change can guarantee four-finger gestures on hardware/firmware that cannot report
them. Do not copy the development machine's touchpad preferences or grant raw input
permissions merely to make installation appear successful.

The new paths need no private script or standalone process. Personal input settings
and bar gestures are preserved. Workspace integration is explicit in the installer
summary, never silently replaces a manual binding, and can be skipped. The stock-Dock
adapter and OkumaDock integration cover their known entry points. Other third-party
docks need the generated desktop entry or explicit activation command; this is not a
compositor-wide launcher override. Refresh the managed stock-Dock clone after Omarchy
updates, and remove Dock integration before uninstalling Launchpad.
