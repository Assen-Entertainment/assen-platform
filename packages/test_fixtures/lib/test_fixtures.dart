/// Shared, deterministic test data builders for Assen Platform.
///
/// Imported as a dev_dependency by other packages so fixtures are defined once.
/// Keep builders pure and seeded (no randomness, no clock reads) so tests stay
/// reproducible across machines and CI.
library;

export 'src/fan_fixtures.dart';
