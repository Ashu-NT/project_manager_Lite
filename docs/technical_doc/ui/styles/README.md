# UI Styles Module

`ui/styles/` provides the visual system used by all tabs and dialogs.

## Files

- `ui_config.py`: centralized sizing, spacing, labels, and UI constants
- `theme_tokens.py`: theme token values (light/dark)
- `theme_stylesheet.py`: stylesheet generators
- `theme.py`: runtime theme apply entrypoints
- `style_utils.py`: table and widget styling helpers
- `formatting.py`: numeric/currency/ratio display helpers

## Theming Architecture

Runtime flow:

1. persisted mode is loaded from settings
2. `theme.set_theme_mode(...)` applies token set
3. `theme.apply_app_style(...)` applies full stylesheet to application

Tokens and stylesheet generation are separated so the codebase can evolve visual
design with minimal behavioral coupling.

## UI Configuration Contract (`UIConfig`)

`UIConfig` acts as a shared contract for:

- control dimensions (button heights, input heights)
- spacing and margins
- text labels used in UI controls
- style snippets for recurrent visual components

This avoids hard-coded magic numbers in tab modules.

## Formatting Contract

`formatting.py` ensures consistent display for:

- integers and floats
- percentages
- currency values and currency symbols
- ratio metrics

These helpers prevent formatting drift across dashboards, reports, and dialogs.

## Table Styling

`style_utils.py` centralizes:

- table stylesheet application
- column auto-fit scheduling and resize signal binding
- safe QObject-alive checks to avoid deleted-object runtime errors
