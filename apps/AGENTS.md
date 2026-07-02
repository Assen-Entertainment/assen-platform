# AGENTS.md — apps/ + packages/ (Flutter)

Pub workspace (Melos 7). Run tasks from the repo root with `dart run melos run <script>`.

## Rules (incident-based, CONSTRAINTS #34/#40)

- Riverpod **3.x only**. 2.x syntax (`StateNotifier`, `ChangeNotifierProvider` patterns, `ref.read` misuse) is forbidden — the analyzer/codegen hallucinate 2.x; reject it in review.
- Theme and shared widgets come from `ui_kit`. Do not hard-code colors/spacing in apps or feature packages; thread through `ui_kit` / `core_tokens`.
- `operator_features` is operator-only. `fan_app` must **never** depend on it (and vice-versa for fan-only surfaces).
- Every public Dart symbol needs a `///` doc comment (explains *why*, not *what*).
- Never run `flutter test --update-goldens` autonomously — goldens are human-gated (CONSTRAINTS #31).
- Do not edit generated files (`*.g.dart`, `*.freezed.dart`, `api_client/lib/src/generated/`); re-run the generator instead.

## Verify (machine-checkable, run from repo root)

- Format: `dart run melos run format`
- Analyze: `dart run melos run analyze`
- All tests: `dart run melos run test`
- One file fast: `flutter test packages/<pkg>/test/<file>_test.dart`
