# Organism golden baselines — pending human approval (#31)

Every organism test declares a pixel `goldenTest(...)` with **`skip: true`**. The
baseline PNGs under `goldens/` are intentionally **not generated** here:
`flutter test --update-goldens` is a human-gated action (CONSTRAINTS #31,
`scripts/hooks/guard.py` blocks both the `goldens/` path and the
`--update-goldens` flag).

What the skipped golden tests prove today:

- the golden harness (`alchemist`) is wired up and the scenarios are collected;
- removing `skip` is the only step left once a human approves the baseline.

## How a human approves the baselines (gate #31)

From `packages/ui_kit`:

```sh
flutter test --update-goldens        # human runs this; agents cannot
```

Then drop `skip: true` from each `goldenTest(...)` and commit the generated
`goldens/**` PNGs in the same human-reviewed change.

The interactive/render/variant/state behaviour of every organism is already
covered by non-skipped `testWidgets` assertions in the sibling `*_test.dart`
files, so the organisms are verified independently of the pixel baselines.
