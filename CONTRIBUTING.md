# Contributing

Use English for code, comments, UI labels, documentation, and tests. The branded
author name may retain its macron. Application-supplied names are not translated.

## Automated checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Portable tests cover icon indexing, XDG precedence, URI encoding, manifest identity,
and project language. They do not replace QML loading or physical gesture tests.

## Manual desktop checklist

- Install to a clean user plugin directory; validate, enable, and rescan.
- Check shell logs for QML errors before summoning.
- Summon/hide repeatedly, including reopening during the exit transition.
- Verify the overlay uses the focused monitor and does not reserve desktop space.
- Check both light and dark themes and a changed bar font.
- Search by name/keyword; test no results, Enter, Escape, arrows, and Tab navigation.
- Launch normal and terminal applications; confirm desktop Exec field handling.
- Scroll with a wheel and touchpad, including momentum and boundary conditions.
- Test missing icon themes, missing artwork, and startup before the index completes.
- Add/remove an application while the shell runs; check icon refresh.
- Test four-finger open and three/four-finger close on real hardware.
- Confirm existing workspace swipes, bar gestures, and three-finger dragging remain.
- Test disable/enable, plugin reload, logout/login, and system reboot.
- Confirm the original standalone launcher is not also bound during migration.

Never modify packaged `/usr/share/omarchy` files for installation or testing.
Describe the tested Omarchy/Quickshell/Hyprland APIs when reporting compatibility.
