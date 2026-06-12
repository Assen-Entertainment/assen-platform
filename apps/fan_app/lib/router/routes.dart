/// Route path + name constants for the fan app (plan §4.3).
///
/// Centralising the literals keeps `context.go(...)` call sites and the route
/// table from drifting, and gives tests one place to reference paths. Names are
/// used for `goNamed`/deep-link targets where a stable identifier helps.
library;

/// Fan-app route locations. Paths only; the tree is built in `fan_router.dart`.
abstract final class FanRoutes {
  /// Onboarding carousel — mobile first-run entry (plan §4.3).
  static const String onboarding = '/onboarding';

  /// Login — Flutter web entry point and the unauthenticated redirect target.
  static const String login = '/login';

  /// Signup flow entry (A2 약관 → A3 본인인증 → A4 닉네임, static stubs).
  static const String signup = '/signup';

  /// Home tab (C0) — first post-auth destination.
  static const String home = '/home';

  /// Schedule tab (C1 출근표).
  static const String schedule = '/schedule';

  /// Reservation tab (D1) — placeholder, no template yet.
  static const String reservation = '/reservation';

  /// Cheki album tab (E1).
  static const String cheki = '/cheki';

  /// My-page hub tab (F1) — placeholder.
  static const String my = '/my';

  /// Visit history nested under the My tab (E2).
  static const String visitHistory = '/my/visits';

  /// Event list (C4).
  static const String events = '/events';

  /// Event detail (C5). Deep-linkable: `/events/:id`.
  static const String eventName = 'event';

  /// Builds the event detail path for [id] (e.g. `/events/mio-birthday-week`).
  static String eventPath(String id) => '/events/$id';

  /// Cast profile detail (C3). Deep-linkable: `/cast/:id`.
  static const String castName = 'cast';

  /// Builds the cast profile path for [id] (e.g. `/cast/mio`).
  static String castPath(String id) => '/cast/$id';

  /// Rotating QR check-in (B1) — deep-link entry point.
  static const String qr = '/qr';

  /// Check-in complete (B2) — completion placeholder.
  static const String checkinComplete = '/checkin/complete';
}
