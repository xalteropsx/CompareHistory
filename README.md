# 📊 CompareHistory

**A powerful file comparison and version history plugin for Sublime Text.**

---

## 📖 Description

CompareHistory combines **side-by-side file comparison** with **automatic version history tracking**. Every time you save a file, a version is stored. You can compare any two versions, see differences highlighted, and navigate through changes easily.

---

## 🙏 Thanks

Inspired by [Compare Side-By-Side](https://github.com/kaste/Compare-Side-By-Side) – thanks to [kaste](https://github.com/kaste)!

## ✨ Key Features

- **📊 Side-by-Side Comparison** – Compare files, selections, or versions
- **💾 Automatic Version History** – Saves versions on every save (configurable limit)
- **🎨 Color Highlighting** – Red = removed, Green = added, with intra-line diff support
- **🔄 Synchronized Scrolling** – Both panes scroll together
- **📂 Project-Aware** – Versions stored per project folder
- **⚡ Fast Grid View** – Compare up to 6 versions simultaneously

---

## ⌨️ Key Bindings

| Command | Keybinding |
|---------|------------|
| Show Version History | `Ctrl+Shift+V` |
| Clear File History | `Ctrl+Shift+Delete` |
| Settings | `Ctrl+Shift+,` |

<details>
<summary>Additional Commands (commented out by default)</summary>

| Command | Keybinding |
|---------|------------|
| Compare Selections | *(uncomment to enable)* |
| Mark Target Selection | *(uncomment to enable)* |
| Compare with Active View | *(uncomment to enable)* |
| Next Difference | `Ctrl+Shift+N` |
| Previous Difference | `Ctrl+Shift+P` |

</details>

---

## 🖱️ Context Menu

Right-click anywhere in a file to access:

| Menu Item | Description |
|-----------|-------------|
| **Compare with Tab** | Compare current file with another open tab |
| **Compare Selections** | Compare two selected text blocks |
| **Mark Target Selection** | Mark current selection for later comparison |
| **Compare with Active View** | Compare with view in other group |
| **Compare with Last View** | Compare with last compared file |
| **Next / Previous** | Navigate between differences |
| **Show Version History** | View and compare all saved versions |
| **Clear File History** | Delete all versions for current file |
| **Settings** | Configure plugin |

---

## 🛠️ Settings

Access via `Ctrl+Shift+,` or menu: **Preferences → Package Settings → CompareHistory**

### Available Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `versioned_history_base` | Where to store version history | `~/.cache` |
| `versioned_history_limit` | Max versions to keep per file | `10` |


| Setting | Description | ReadOnly |
|---------|-------------|---------|
| `read_only` | Make comparison views read-only | `false` |
| `ignore_whitespace` | Ignore spaces when comparing | `false` |
| `ignore_case` | Case-insensitive comparison | `false` |
| `ignore_pattern` | Regex pattern to ignore | `""` |
| `outlines_only` | Show outlines instead of filled regions | `false` |
| `hide_sidebar` | Hide sidebar in comparison window | `false` |
| `hide_menu` | Hide menu bar | `false` |
| `hide_minimap` | Hide minimap | `false` |
| `hide_status_bar` | Hide status bar | `false` |
| `hide_tabs` | Hide tabs | `false` |
| `display_prefix` | Prefix for view names | `""` |
| `line_count_popup` | Show diff count in popup | `false` |

---



## How to Enable CompareHistory Key Settings

```json
[
    { "keys": ["ctrl+shift+v"], "command": "ch_show_version_history" },
    { "keys": ["ctrl+shift+delete"], "command": "ch_clear_file_history" },
    { "keys": ["ctrl+shift+,"], "command": "ch_versioned_hx_settings" }
    { "keys": ["ctrl+shift+n"], "command": "ch_next_diff" },
    { "keys": ["ctrl+shift+p"], "command": "ch_prev_diff" },
    { "keys": [], "command": "ch_comparex", "args": {"compare_selections": true} },
    { "keys": [], "command": "ch_mark_selx" },
    { "keys": [], "command": "ch_comparex", "args": {"with_active": true} },
    { "keys": ["ctrl+shift+t"], "command": "ch_comparex" },
    { "keys": ["ctrl+shift+l"], "command": "ch_comparex", "args": {"last_selections": true} }
]
```

1. Open **Command Palette** (`Ctrl+Shift+P`)
2. Type `Preferences: Key Bindings`
3. Copy the desired line
4. Save the file


## 📁 Storage Location

Versions are stored at:
