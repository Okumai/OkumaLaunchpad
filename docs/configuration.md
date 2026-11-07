# Configuration

Merge settings into the existing `okuma.dev_launchpad4omarchy` entry in the shell's `plugins`
array. Do not replace the entire shell configuration. `XDG_CONFIG_HOME` is respected.
Settings reload live. Numeric values are clamped to the ranges below; other types
use defaults.

| Setting | Default | Range | Meaning |
| --- | --- | --- | --- |
| `scrollSensitivity` | 3 | 0.25-10 | Local wheel/touchpad scroll multiplier |
| `openDuration` | 90 | 0-500 | Opening transition duration in milliseconds |
| `closeDuration` | 70 | 0-500 | Closing transition duration in milliseconds |
| `searchWidth` | 300 | 160-600 | Maximum search width in logical pixels |
| `cellSize` | 140 | 100-220 | Grid cell size in logical pixels |
| `iconSize` | 64 | 24-80 | Application icon size in logical pixels |
| `backgroundOpacity` | 0.94 | 0.3-1 | Theme-colored overlay opacity multiplier |

Colors come from `qs.Commons.Color.menu` and the shared muted color. The font follows
the active Omarchy bar, with the shared style font as fallback. The wallpaper comes
from `$XDG_STATE_HOME/omarchy/current/background` or the standard home-directory fallback.
Application artwork keeps its original colors.

The launcher does not change global scroll speed, touchpad settings, icon themes,
workspace gestures, or bar visibility.
