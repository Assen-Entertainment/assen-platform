/// A minimal fan record used across tests.
///
/// Placeholder shape for P0; the real domain model lands with the `fan` feature
/// (P3+). It exists now so packages share one fixture type instead of each
/// redefining ad-hoc maps.
class FanFixture {
  /// Creates a fan fixture with the given [id] and [displayName].
  const FanFixture({required this.id, required this.displayName});

  /// Stable identifier for the fan.
  final String id;

  /// Name shown in the UI.
  final String displayName;
}

/// Deterministic fixture builders. Methods are pure so tests are reproducible.
abstract final class Fixtures {
  /// Returns a canonical sample fan.
  ///
  /// Override [id] or [displayName] for cases that need a distinct fan; the
  /// defaults are fixed so equality-by-value assertions are stable.
  static FanFixture fan({
    String id = 'fan-001',
    String displayName = 'Hatsukoi Guest',
  }) {
    return FanFixture(id: id, displayName: displayName);
  }
}
