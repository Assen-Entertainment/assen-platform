import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/dashboard/operator_dashboard_repository.dart';

void main() {
  group('InMemoryOperatorDashboardRepository', () {
    test('metrics use the injected now for the default business day', () {
      final repo = InMemoryOperatorDashboardRepository(
        now: DateTime(2026, 6, 15, 10),
      );
      final metrics = repo.metrics();

      expect(metrics.businessDay, '2026-06-15');
      expect(metrics.visits, 38);
      expect(metrics.cheki, 27);
      expect(metrics.reservations, 12);
      expect(metrics.favorites, 9);
      expect(metrics.safetyReportsOpen, 1);
    });

    test('an explicit day overrides the business day', () {
      final repo = InMemoryOperatorDashboardRepository(
        now: DateTime(2026, 6, 15),
      );

      expect(repo.metrics(day: DateTime(2026, 1, 2)).businessDay, '2026-01-02');
    });
  });

  group('dashboardMetricsCsv', () {
    const metrics = OperatorDashboardMetrics(
      businessDay: '2026-06-15',
      visits: 38,
      cheki: 27,
      reservations: 12,
      favorites: 9,
      safetyReportsOpen: 1,
    );

    test('renders a counts-only header + value row, CRLF terminated', () {
      final csv = dashboardMetricsCsv(metrics);
      final lines = csv.split('\r\n');

      // Header, value row, then the trailing-CRLF empty tail.
      expect(lines, hasLength(3));
      expect(lines[0], kDashboardCsvColumns.join(','));
      expect(lines[1], '2026-06-15,38,27,12,9,1');
      expect(lines[2], isEmpty);
      expect(csv.endsWith('\r\n'), isTrue);
    });

    test('columns match the server DashboardOut field order', () {
      expect(kDashboardCsvColumns, <String>[
        'business_day',
        'visits',
        'cheki',
        'reservations',
        'favorites',
        'safety_reports_open',
      ]);
    });
  });
}
