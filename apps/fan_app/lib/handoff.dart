/// The Vite-landing -> Flutter-app handoff URL contract (single source).
///
/// The public landing (`landing/`, Vite) and the app (Flutter web) ship
/// separately; the landing's `/` is not a Flutter route, and the Flutter web
/// entry point is `/login` (plan §4.3). This class fixes the query-parameter
/// names the landing CTA uses when it redirects into the app, and the
/// `return_to` safety rules the guard enforces. Documented in
/// `docs/design/handoff.md`; the landing directory itself is a separate track
/// and is not edited here.
library;

/// Names and rules for the landing -> app handoff. Pure constants + parsing; no
/// Flutter dependency so it is trivially unit-testable.
abstract final class LandingHandoff {
  /// Query key carrying the in-app path to return to after auth (e.g. `/qr`).
  static const String returnToParam = 'return_to';

  /// Standard UTM attribution keys forwarded by the landing CTA. The app reads
  /// them for analytics only; they never affect navigation.
  static const String utmSourceParam = 'utm_source';

  /// UTM medium/placement key.
  static const String utmMediumParam = 'utm_medium';

  /// UTM campaign key.
  static const String utmCampaignParam = 'utm_campaign';

  /// Where to land after auth when no (valid) `return_to` was supplied.
  static const String defaultReturnTo = '/home';

  /// Validates a raw `return_to` value, returning a safe in-app path.
  ///
  /// Allowlist parse (handoff.md §3): the value must parse as a relative
  /// reference with no scheme and no authority whose path is rooted (`/...`)
  /// but not scheme-relative (`//host`). Backslash and TAB/LF/CR are rejected
  /// outright because WHATWG URL parsing strips control characters and treats
  /// `\` as `/` — so `/\evil.com` or a TAB-split `//evil.com` would otherwise
  /// re-normalise into an off-origin redirect in the browser. A colon in the
  /// query or fragment (e.g. `?t=12:30`) is legitimate and allowed.
  static String safeReturnTo(String? raw) {
    if (raw == null || raw.isEmpty) return defaultReturnTo;
    if (raw.contains(r'\') ||
        raw.contains('\t') ||
        raw.contains('\n') ||
        raw.contains('\r')) {
      return defaultReturnTo;
    }
    final uri = Uri.tryParse(raw);
    if (uri == null) return defaultReturnTo;
    final isRootedInAppPath =
        !uri.hasScheme &&
        !uri.hasAuthority &&
        uri.path.startsWith('/') &&
        !uri.path.startsWith('//');
    return isRootedInAppPath ? raw : defaultReturnTo;
  }
}
