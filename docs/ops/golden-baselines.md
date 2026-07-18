# Golden baselines runbook (ui_kit, #31)

`ui_kit` ships a pixel `goldenTest(...)` for every atom/molecule/organism, but
each is declared `skip: true` with a `// … (#31)` marker and **no baseline PNG
is committed**. This is deliberate:

- `scripts/hooks/guard.py` (#31) hard-blocks both the `goldens/` write path and
  the `--update-goldens` flag on local (non-CI) machines, and
- baselines must render on **CI Linux**, not a developer's Windows box, or the
  pixels would never match in CI.

The `.github/workflows/golden.yml` workflow turns the #31 human-approval gate
into a **one-click CI action**.

## The two jobs

| Job | Trigger | What it does |
| --- | --- | --- |
| `verify` | every PR touching `packages/ui_kit/**` (or this workflow) | Runs `flutter test` in `packages/ui_kit` on `ubuntu-latest`. While the goldens are still `skip: true` with no committed baseline this is a **no-op for the pixel scenarios** (they are skipped); the non-golden `testWidgets` still gate. Once baselines land + are unskipped, this becomes the real golden-regression gate. |
| `generate` | manual **Run workflow** (`workflow_dispatch`) | Unskips the #31 golden tests, generates the Linux baselines with `--update-goldens`, and auto-commits the result. This is the #31 human approval. |

## One-click approval (generate the baselines)

When a human is ready to approve the ui_kit golden baselines:

1. Push the branch you want the baselines committed to (e.g. a
   `feature/ui_kit-goldens` branch, or `dev`).
2. GitHub → **Actions** → **Golden baselines** → **Run workflow** → pick that
   branch → **Run workflow**.
3. The `generate` job (on CI Linux) then, atomically:
   1. **Unskips** only the golden tests carrying the `(#31)` marker — it deletes
      the `skip: true, // … (#31)` line and nothing else (a `sed` targeting that
      exact marker), so any unrelated skip is left untouched.
   2. Runs `flutter test --update-goldens` in `packages/ui_kit`, which now
      executes the unskipped tests and writes the baseline PNGs under
      `packages/ui_kit/test/**/goldens/`.
   3. Commits the unskipped test files **and** the generated PNGs back to the
      dispatched branch via `stefanzweifel/git-auto-commit-action`
      (`file_pattern: packages/ui_kit/test/**`).

> Unskip happens **before** `--update-goldens` on purpose: a `skip: true` test
> never runs, so it would produce no baseline.

After that commit, `verify` on subsequent PRs compares every ui_kit widget to
the approved Linux baseline; a render change that moves pixels fails the PR
until the baseline is regenerated (re-run the `generate` job).

## Do NOT do this locally

- **Never** run `flutter test --update-goldens` locally — the #31 guard blocks
  it, and Windows-rendered PNGs are not valid CI baselines.
- **Never** hand-remove `skip: true` locally: without a committed baseline the
  test goes red immediately. Unskip + baseline generation must happen together,
  which is exactly what the `generate` job does atomically on CI.
- **Never** hand-write / commit golden PNG files — the guard blocks the
  `goldens/` path.

The interactive/render/variant behaviour of every widget is already covered by
non-skipped `testWidgets` assertions, so the catalogue stays verified even
before the pixel baselines are approved (see the `GOLDENS_PENDING.md` notes
under `packages/ui_kit/test/`).
