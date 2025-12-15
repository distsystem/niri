---
name: niri
description: Configure niri Wayland compositor. Use for editing KDL config files, adding keybinds, window rules, layout settings, environment variables, or autostart programs. Triggers on niri config tasks in ~/.config/niri/.
---

# Niri Configuration

## Config Structure

Modular KDL config in `~/.config/niri/`:

```
config.kdl          # Entry point, includes conf.d/*
conf.d/
  env.kdl           # Environment variables
  misc.kdl          # Screenshot path, hotkey-overlay, prefer-no-csd
  input.kdl         # Keyboard, touchpad settings
  output.kdl        # Monitor configuration
  layout.kdl        # Gaps, focus-ring, border, shadow, animations
  autostart.kdl     # spawn-at-startup commands
  rules.kdl         # Window rules (match app-id, open-floating, etc.)
  binds.kdl         # All keybindings
scripts/            # Helper scripts (Python/Bash)
```

## KDL Syntax Quick Reference

```kdl
// Comment
node "arg1" "arg2" key=value { children }

// Include other files
include "conf.d/file.kdl"

// Environment
environment {
    VAR_NAME "value"
}

// Keybinds
binds {
    Mod+Key { action; }
    Mod+Key { action "arg"; }
    Mod+Key { spawn "cmd" "arg1" "arg2"; }
    Mod+Key { spawn-sh "shell command with pipes"; }
    Mod+Key repeat=false { action; }
    Mod+Key allow-when-locked=true { action; }
    Mod+Key cooldown-ms=150 { action; }
}

// Layout
layout {
    gaps 15
    default-column-width { proportion 0.5; }
    preset-column-widths {
        proportion 0.5
        proportion 0.667
        proportion 1.0
    }
    focus-ring {
        width 3
        active-color "#7fc8ff"
        inactive-color "#505050"
    }
    border { off }
    shadow {
        on
        softness 30
        spread 5
        offset x=0 y=5
        color "#0007"
    }
    center-focused-column "on-overflow"  // "never" | "always" | "on-overflow"
}

// Window rules
window-rule {
    match app-id="app-name"
    match title="regex"
    open-floating true
    open-maximized true
    open-on-workspace "name"
}

// Autostart
spawn-at-startup "command" "arg1" "arg2"
```

## Common Actions

**Window focus/move:**
- `focus-column-left/right`, `focus-window-down/up`
- `focus-window-or-workspace-down/up`
- `move-column-left/right`, `move-window-down/up`
- `consume-or-expel-window-left/right`

**Resize:**
- `set-column-width "+10%"` / `set-column-width "-10%"`
- `set-window-height "+10%"` / `set-window-height "-10%"`
- `switch-preset-column-width`, `switch-preset-window-height`
- `expand-column-to-available-width`

**Layout:**
- `toggle-window-floating`, `fullscreen-window`
- `close-window`, `quit`

**Workspace:**
- `focus-workspace N`, `focus-workspace-up/down`
- `focus-workspace-previous`
- `move-column-to-workspace N`
- `move-column-to-workspace-up/down`

**Monitor:**
- `focus-monitor-left/right`
- `move-column-to-monitor-left/right`

**Other:**
- `toggle-overview`, `show-hotkey-overlay`
- `screenshot`, `screenshot-window`, `screenshot-screen`
- `toggle-keyboard-shortcuts-inhibit`

## Helper Scripts

Located in `scripts/`:

- **niri_spawnjump.py** - Spawn or jump to existing app instance
- **niri_workspace_helper.py** - Enhanced workspace switching with overview toggle
- **niri_peekaboo.py** - Pull nearby windows as floats
- **niri_window_details.sh** - Show focused window info via notification
- **fuzzel_helper.sh** - Toggle launcher on/off

## References

- Official wiki: https://github.com/YaLTeR/niri/wiki
- Default config: https://github.com/YaLTeR/niri/blob/main/resources/default-config.kdl
- IPC docs: https://github.com/YaLTeR/niri/wiki/IPC
