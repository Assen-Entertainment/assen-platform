import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/safety/operator_safety_repository.dart';

/// Repository provider for operator safety data.
final Provider<OperatorSafetyRepository> operatorSafetyRepositoryProvider =
    Provider<OperatorSafetyRepository>(
      (ref) => InMemoryOperatorSafetyRepository(),
    );

/// The viewer's role for the safety console — the RBAC surface seam.
///
/// Defaults to [SafetyViewerRole.operator] (fail-closed): the operator router
/// guard is still a P3a stub that admits any non-expired session, so until
/// real role claims gate the console (P3b) the safe default is the
/// least-privileged surface — detail fields redacted, manager-only resolve /
/// block hidden. Tests override this provider to [SafetyViewerRole.manager] to
/// exercise the manager surface.
final Provider<SafetyViewerRole> safetyViewerRoleProvider =
    Provider<SafetyViewerRole>((ref) => SafetyViewerRole.operator);

/// Controller provider for the O4 safety report console.
final operatorSafetyControllerProvider =
    NotifierProvider<OperatorSafetyController, List<OperatorSafetyReport>>(
      OperatorSafetyController.new,
    );

/// Riverpod 3 controller that keeps the report list fresh after each action.
class OperatorSafetyController extends Notifier<List<OperatorSafetyReport>> {
  OperatorSafetyRepository get _repo =>
      ref.read(operatorSafetyRepositoryProvider);

  @override
  List<OperatorSafetyReport> build() => _repo.listReports();

  /// The next handling status after [status], or null when there is no plain
  /// transition (actioned closes via [resolveReport]; closed is terminal).
  OperatorReportStatus? nextStatusAfter(OperatorReportStatus status) =>
      switch (status) {
        OperatorReportStatus.received => OperatorReportStatus.reviewing,
        OperatorReportStatus.reviewing => OperatorReportStatus.actioned,
        OperatorReportStatus.actioned => null,
        OperatorReportStatus.closed => null,
      };

  /// Advances [report] to its next handling status (no-op when terminal).
  void advanceStatus(OperatorSafetyReport report) {
    final next = nextStatusAfter(report.status);
    if (next == null) return;
    _repo.advanceStatus(reportId: report.id, status: next);
    _refresh();
  }

  /// Closes a report with a restricted-store resolution note (manager+).
  void resolveReport({
    required String reportId,
    required String resolutionNote,
  }) {
    _repo.resolveReport(reportId: reportId, resolutionNote: resolutionNote);
    _refresh();
  }

  /// Blocks or risk-flags the target of [reportId] (manager+).
  void blockUser({
    required String reportId,
    required OperatorBlockScope scope,
    required OperatorBlockReason reason,
    required bool isRiskFlag,
  }) {
    _repo.blockUser(
      reportId: reportId,
      scope: scope,
      reason: reason,
      isRiskFlag: isRiskFlag,
    );
    _refresh();
  }

  void _refresh() => state = _repo.listReports();
}
