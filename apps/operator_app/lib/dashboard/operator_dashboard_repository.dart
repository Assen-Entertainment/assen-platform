import 'package:flutter/foundation.dart';

// The repository below is a deliberate one-method adapter seam: the real HTTP
// client implementation lands behind it, mirroring the other operator console
// repositories (safety/schedule) which differ only by having more methods.
// ignore_for_file: one_member_abstracts

/// Viewer role for the operator dashboard — the RBAC surface seam.
///
/// Mirrors the server's tiered access (`admin_rbac`): an [operator] sees the
/// at-a-glance counts and the status-edit entry points, while the admin-only
/// sections (settings / permissions / risk / audit-log — the ASS-97 v1
/// follow-ups named in the server `dashboard.api` docstring) are reserved for a
/// [manager]. Real role claims arrive with the auth token in a later issue (see
/// `operator_router` P3b); until then this is the presentation seam that lets
/// the manager surface be exercised in the mock.
enum DashboardViewerRole {
  /// operator+ — at-a-glance counts and status-edit entry points only.
  operator,

  /// manager+ — additionally sees the admin-only sections.
  manager,
}

/// At-a-glance operator dashboard counts for one business day.
///
/// A 1:1 mirror of the server `DashboardOut` schema
/// (`GET /api/operator/dashboard`): counts only, no personal data. The real API
/// client adapter lands later behind [OperatorDashboardRepository]; this is the
/// shape both the mock and that adapter produce.
@immutable
class OperatorDashboardMetrics {
  /// Creates an immutable dashboard metrics snapshot.
  const OperatorDashboardMetrics({
    required this.businessDay,
    required this.visits,
    required this.cheki,
    required this.reservations,
    required this.favorites,
    required this.safetyReportsOpen,
  });

  /// The day these counts describe, ISO `YYYY-MM-DD` (server `business_day`).
  final String businessDay;

  /// Check-ins recorded in the day window (gross; server `visits`).
  final int visits;

  /// Cheki recorded in the day window (server `cheki`).
  final int cheki;

  /// Reservations created in the day window (server `reservations`).
  final int reservations;

  /// Favorites added in the day window (server `favorites`).
  final int favorites;

  /// Current open-report backlog, all-time (server `safety_reports_open`).
  final int safetyReportsOpen;
}

/// The CSV column order, matching the server `DashboardOut` field names so the
/// daily report export stays consistent with the API contract.
const List<String> kDashboardCsvColumns = <String>[
  'business_day',
  'visits',
  'cheki',
  'reservations',
  'favorites',
  'safety_reports_open',
];

/// Renders [metrics] as a single-row RFC 4180 CSV (header + values).
///
/// Counts only — no names, prices, or other personal data ever enter the
/// export (the ASS-97 daily-report requirement is an at-a-glance gauge, not a
/// PII extract). Lines are CRLF-terminated as RFC 4180 specifies so the file
/// opens cleanly in spreadsheet tools.
String dashboardMetricsCsv(OperatorDashboardMetrics metrics) {
  final values = <Object>[
    metrics.businessDay,
    metrics.visits,
    metrics.cheki,
    metrics.reservations,
    metrics.favorites,
    metrics.safetyReportsOpen,
  ];
  // Every field is an int or an ISO date, so a plain join is RFC 4180-safe; do
  // NOT add free-text (string) fields here without quote-escaping — and adding
  // one would also breach the counts-only/no-PII guarantee.
  final header = kDashboardCsvColumns.join(',');
  final row = values.join(',');
  return '$header\r\n$row\r\n';
}

/// Adapter boundary for operator dashboard data (the API client lands later,
/// behind this same surface — mirroring the ASS-97 server contract). A single
/// method for now; the real HTTP adapter will grow it, so the seam stays.
abstract class OperatorDashboardRepository {
  /// Returns the dashboard counts for [day] (defaults to today).
  ///
  /// Mirrors `GET /api/operator/dashboard?date=`; the real adapter will query
  /// the endpoint per day, while the mock returns deterministic counts.
  OperatorDashboardMetrics metrics({DateTime? day});
}

/// In-memory implementation used until the API client adapter lands.
///
/// The counts are fixed, deterministic placeholders (operator-internal figures,
/// not approved values — screens.md mock rule); only `businessDay` tracks the
/// requested day. `now` anchors the default business day so widget tests are
/// stable.
class InMemoryOperatorDashboardRepository
    implements OperatorDashboardRepository {
  /// Creates the mock repository, anchoring the default day to [now].
  InMemoryOperatorDashboardRepository({DateTime? now})
    : _now = now ?? DateTime.now();

  final DateTime _now;

  @override
  OperatorDashboardMetrics metrics({DateTime? day}) {
    final target = day ?? _now;
    return OperatorDashboardMetrics(
      businessDay: _isoDate(target),
      visits: 38,
      cheki: 27,
      reservations: 12,
      favorites: 9,
      safetyReportsOpen: 1,
    );
  }

  static String _isoDate(DateTime date) {
    final m = date.month.toString().padLeft(2, '0');
    final d = date.day.toString().padLeft(2, '0');
    return '${date.year}-$m-$d';
  }
}
