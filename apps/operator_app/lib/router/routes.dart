/// Route path constants for the operator app (plan §4.3).
///
/// Centralised so `context.go(...)` call sites and the route table share one
/// set of literals. The operator surface is RBAC-gated; P3a stubs the role
/// guard (the real判定 lands in P3b).
library;

/// Operator-app route locations.
abstract final class OperatorRoutes {
  /// Operator login — entry point and the unauthenticated redirect target.
  static const String login = '/login';

  /// Operator dashboard (O1) — first post-auth destination.
  static const String dashboard = '/dashboard';

  /// Check-in processing (O2) — placeholder.
  static const String checkin = '/checkin';

  /// Cheki record entry (O3) — placeholder.
  static const String cheki = '/cheki';

  /// Reports (O4 신고/리포트) — placeholder.
  static const String reports = '/reports';

  /// POS close-out (O5) — placeholder.
  static const String pos = '/pos';

  /// Admin-only area (권한관리 등) — higher-role route slot, placeholder.
  static const String admin = '/admin';
}
