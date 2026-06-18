# Assen web layout subsystem (ASS-147)

The desktop-first **web layout subsystem** is the peer of the mobile design
system: shared `core_tokens` and organisms, but its own responsive structure so
the fan web app fills a desktop browser (e.g. QHD 2560×1440) instead of leaving
a centered reading column with a wide empty gutter. It engages at the Material 3
`large`/`extraLarge` window classes; compact/medium are byte-for-byte the
existing mobile/tablet behaviour.

## Window size classes

`AssenWindowSize` (`window_size.dart`) is the full M3 ladder:

| Class | Width (dp) | Fan chrome |
|-------|-----------|------------|
| `compact` | `< 600` | bottom tab bar |
| `medium` | `600–839` | collapsed navigation rail |
| `expanded` | `840–1199` | extended rail + centered reading column |
| `large` | `1200–1599` | **persistent sidebar + full-width canonical layouts** |
| `extraLarge` | `≥ 1600` | sidebar + widest canonical layouts |

Use `size.atLeast(other)` for "this class and wider" so call sites survive the
un-collapsing of `large`/`extraLarge` from `expanded`.

## Widgets

- **`AssenSidebarShell`** (`sidebar_shell.dart`) — app shell. Below `large` it
  delegates to `AssenAdaptiveShell` verbatim; at `large`+ it shows a fixed
  `AssenLayout.sidebarWidth` (256dp) sidebar and a full-width body.
- **`AssenFeedGrid`** (`feed_grid.dart`) — responsive **Feed**. A `Column` of
  `Row`s (row-major), so widget-tree / screen-reader / focus order matches the
  visual reading order. Column count derives from its own
  `constraints.maxWidth`.
- **`AssenSupportingPaneScaffold`** (`supporting_pane_scaffold.dart`) — M3
  **Supporting Pane** (main + bounded supporting rail; stacks below the
  breakpoint).
- **`AssenListDetailScaffold`** (`list_detail_scaffold.dart`) — M3
  **List-Detail** (list pane beside a detail pane at/above the breakpoint; list
  alone below, with the caller pushing a detail route).

Detail panes that embed an existing screen mount a **chrome-less `*Body`**
variant (no nested `Scaffold`/`AppBar`/bottom CTA): `AssenEventDetailBody`,
`AssenPointsHistoryBody`, `AssenVisitHistoryBody`,
`AssenNotificationSettingsBody`. The route-built full-`Scaffold` templates are
unchanged and remain what each route builds on push / cold deep-link.

## Two rules that prevent layout bugs

1. **Column counts and breakpoints read the LOCAL pane width, never the window
   width (M2).** A 256dp sidebar shrinks the body below the window, so
   window-width math over-counts columns. `AssenFeedGrid` reads its own
   `constraints.maxWidth`; `assenGridCrossAxisCount` must be passed the local
   grid width.
2. **A host that pre-gates the wide path must gate on the SAME width the inner
   scaffold receives.** If the screen enters the wide path on the raw width but
   the scaffold re-measures after screen-margin padding, a narrow band
   (`1200`…`1200 + 2·screenMargin`) renders the screen "wide" while the scaffold
   collapses to list-only — a dead zone where a tap has nowhere to go. Gate the
   host on `constraints.maxWidth − screenMargin·2` so host and scaffold flip
   together. (See `EventListScreen` / `MyHubScaffold`.)

## Selection state for inline detail

Never hold the selected detail in an app-global provider (it would not reset on
re-entry — `indexedStack` never disposes branch navigators). Instead:

- **In-branch routes (`/my/*`)** — derive the selection from `GoRouterState` /
  the URL. Selecting is `context.go('/my/<sub>')`; returning to the branch root
  resets it. Deep-linkable, provider-free.
- **Out-of-shell routes (`/events`, `/cast`)** — keep the selection in
  screen-local state, which auto-disposes with the route on exit.

## Goldens

Pixel golden baselines for these widgets are deferred to the design-review
milestone — see `test/layout/GOLDENS_PENDING.md`.
