import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/dashboard/operator_dashboard_repository.dart';

/// Repository provider for operator dashboard data.
final Provider<OperatorDashboardRepository>
operatorDashboardRepositoryProvider = Provider<OperatorDashboardRepository>(
  (ref) => InMemoryOperatorDashboardRepository(),
);

/// The viewer's role for the dashboard — the RBAC surface seam.
///
/// Defaults to [DashboardViewerRole.operator] (fail-closed): the operator
/// router guard is still a P3a stub that admits any non-expired session, so
/// until real role claims gate the console (P3b) the safe default is the
/// least-privileged surface — the admin-only sections (settings / permissions /
/// risk / audit-log) stay hidden. Tests override this provider to
/// [DashboardViewerRole.manager] to exercise the admin surface.
final Provider<DashboardViewerRole> dashboardViewerRoleProvider =
    Provider<DashboardViewerRole>((ref) => DashboardViewerRole.operator);

/// Controller provider for the operator dashboard (O1).
final operatorDashboardControllerProvider =
    NotifierProvider<OperatorDashboardController, OperatorDashboardMetrics>(
      OperatorDashboardController.new,
    );

/// Riverpod 3 controller that exposes the day's dashboard counts, refreshable
/// once the real API client adapter replaces the mock repository.
class OperatorDashboardController extends Notifier<OperatorDashboardMetrics> {
  OperatorDashboardRepository get _repo =>
      ref.read(operatorDashboardRepositoryProvider);

  @override
  OperatorDashboardMetrics build() => _repo.metrics();

  /// Re-reads the counts (the seam the future API client refetch hooks into).
  void refresh() => state = _repo.metrics();
}
