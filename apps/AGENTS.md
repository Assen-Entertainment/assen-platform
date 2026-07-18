# AGENTS.md — apps/ + packages/ (Flutter)

Pub workspace (Melos 7). Run tasks from the repo root with `dart run melos run <script>`.

Structure after the platform pivot (Linear B9/M10): the 메이드-era apps
(`fan_app`/`operator_app`) and domain feature packages (`features`/
`operator_features`) were removed — git history is their archive. The workspace
is now the new-direction app `apps/assen_mobile` on top of the reusable
`core_tokens` (tokens), `ui_kit` (design system), `api_client` (B-API contract),
and `test_fixtures` packages.

## Rules (incident-based, CONSTRAINTS #34/#40)

- Riverpod **3.x only**. 2.x syntax (`StateNotifier`, `ChangeNotifierProvider` patterns, `ref.read` misuse) is forbidden — the analyzer/codegen hallucinate 2.x; reject it in review.
- Theme and shared widgets come from `ui_kit`. Do not hard-code colors/spacing in the app; thread through `ui_kit` / `core_tokens`.
- `ui_kit` mirrors the web design system (`web/src/components/ui`). Keep it domain-agnostic — no product-specific screens/widgets leak into it; those live in `apps/assen_mobile`.
- Every public Dart symbol needs a `///` doc comment (explains *why*, not *what*).
- Never run `flutter test --update-goldens` autonomously — goldens are human-gated (CONSTRAINTS #31).
- Do not edit generated files (`*.g.dart`, `*.freezed.dart`, `api_client/lib/src/generated/`); re-run the generator instead.

## Verify (machine-checkable, run from repo root)

- Format: `dart run melos run format`
- Analyze: `dart run melos run analyze`
- All tests: `dart run melos run test`
- One file fast: `flutter test packages/<pkg>/test/<file>_test.dart`
