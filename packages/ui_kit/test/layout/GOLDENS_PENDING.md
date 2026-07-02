# Web layout subsystem — pending golden baselines (ASS-147 Slice 5)

The fan web desktop information architecture (ASS-147) added a new **web layout
subsystem** to `ui_kit` — the desktop-first peer of the mobile design system.
Its widgets are pinned by **geometry/behaviour widget tests** (column counts,
pane order, breakpoint collapse, selection reset), which are deterministic and
already green. Pixel **golden** baselines for these widgets are intentionally
**not generated yet**.

## Why goldens are deferred (not skipped silently)

Per the repo convention, **golden / pixel baselines are a human gate** (a
designer confirms the rendering before a baseline is committed; a baseline is a
visual contract, not an auto-generated artifact). ASS-147 Slice 5 is itself a
**manual design-review milestone (M4)**: a human reviewer confirms the Figma
"Web" page matches the shipped layouts. Golden baselines should be generated
**after** that design review signs off, so the committed pixels match an
approved design — not before.

Until then, coverage is provided by the geometry/behaviour tests listed below,
which assert the *structure* (what golds would also catch as layout shifts)
without freezing pixels prematurely.

## Widgets awaiting a golden baseline

| Widget | File | Behaviour tests covering it today |
|--------|------|-----------------------------------|
| `AssenSidebarShell` | `lib/src/layout/sidebar_shell.dart` | `test/layout/sidebar_shell_test.dart` |
| `AssenFeedGrid` | `lib/src/layout/feed_grid.dart` | `test/layout/feed_grid_test.dart`*, `apps/fan_app/test/home_supporting_pane_layout_test.dart` |
| `AssenSupportingPaneScaffold` | `lib/src/layout/supporting_pane_scaffold.dart` | `apps/fan_app/test/home_supporting_pane_layout_test.dart`, `cast_profile_wide_test.dart` |
| `AssenListDetailScaffold` | `lib/src/layout/list_detail_scaffold.dart` | `test/layout/list_detail_scaffold_test.dart`, `apps/fan_app/test/events_list_detail_test.dart`, `my_list_detail_test.dart` |
| `AssenEventDetailBody` | `lib/src/templates/event_template.dart` | `apps/fan_app/test/events_pane_embed_test.dart` |
| `AssenPointsHistoryBody` / `AssenVisitHistoryBody` / `AssenNotificationSettingsBody` | `lib/src/templates/{points_history,visit_history,notification_settings}_template.dart` | `apps/fan_app/test/points_history_dense_list_test.dart`, `my_list_detail_test.dart` |

\* If a dedicated `feed_grid_test.dart` is not present, the feed grid's
row-major column logic is covered by `columnsForWidth` assertions in the
home/schedule wide-layout tests.

## How to generate the baselines (after design sign-off)

1. Land the Slice 5 Figma "Web" page and get the M4 design review sign-off.
2. Author golden tests under `test/layout/` (or `test/golden/`) using the
   existing golden harness (see `test/token_swatch_golden_test.dart` for the
   project's `alchemist`/golden setup).
3. Generate baselines with `flutter test --update-goldens` for those files only.
4. Have the designer confirm the generated PNGs match the approved Figma page,
   then commit the baselines.

Do **not** auto-generate or commit baselines as part of an automated run — the
sign-off is the gate.
