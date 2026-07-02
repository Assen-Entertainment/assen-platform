import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/dashboard/operator_dashboard_providers.dart';
import 'package:operator_app/dashboard/operator_dashboard_repository.dart';
import 'package:operator_app/router/routes.dart';
import 'package:ui_kit/ui_kit.dart';

/// The operator dashboard (O1) — renders [AssenOperatorDashboardTemplate] wired
/// to live data (ASS-97 v1).
///
/// The template is reused whole (app bar + 신고 notice + segmented views + stat
/// grid + 예약 board); this screen overrides its data-bearing parameters from
/// the [operatorDashboardControllerProvider] and adds the v1 affordances the
/// server `dashboard.api` docstring deferred: status-edit entry points (jump to
/// the 신고/출근표/체크인/체키 consoles), a counts-only CSV export, and the
/// admin-only sections. The admin sections are gated by
/// [dashboardViewerRoleProvider], which defaults fail-closed to operator (the
/// P3a router stub admits any session, so the least-privileged surface is the
/// safe default until P3b role claims land). It is the operator's post-auth
/// root, so no back affordance is shown.
class OperatorDashboardScreen extends ConsumerWidget {
  /// Creates the operator dashboard.
  const OperatorDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final metrics = ref.watch(operatorDashboardControllerProvider);
    final role = ref.watch(dashboardViewerRoleProvider);
    final isManager = role == DashboardViewerRole.manager;

    return AssenOperatorDashboardTemplate(
      businessDayLabel: metrics.businessDay,
      stats: _statsFor(metrics),
      noticeMessage: _noticeFor(metrics.safetyReportsOpen),
      onNoticeTap: () => context.go(OperatorRoutes.reports),
      quickActions: _quickActions(context),
      adminActions: isManager ? _adminActions(context) : const [],
      onExportCsv: () => unawaited(_exportCsv(context, metrics)),
    );
  }

  /// Maps the live counts onto the template's stat grid (no deltas — the v0
  /// endpoint has no prior-day comparison, so no trend is fabricated).
  List<AssenDashboardStat> _statsFor(OperatorDashboardMetrics metrics) {
    return <AssenDashboardStat>[
      AssenDashboardStat(
        value: '${metrics.visits}',
        label: '오늘 방문',
        icon: Icons.login_outlined,
      ),
      AssenDashboardStat(
        value: '${metrics.reservations}',
        label: '예약',
        icon: Icons.event_available_outlined,
      ),
      AssenDashboardStat(
        value: '${metrics.cheki}',
        label: '체키 발행',
        icon: Icons.photo_camera_outlined,
      ),
      AssenDashboardStat(
        value: '${metrics.favorites}',
        label: '즐겨찾기',
        icon: Icons.favorite_border,
      ),
      AssenDashboardStat(
        value: '${metrics.safetyReportsOpen}',
        label: '신고 대기',
        icon: Icons.shield_outlined,
      ),
    ];
  }

  String _noticeFor(int openReports) =>
      openReports > 0 ? '신고 $openReports건이 처리 대기 중입니다.' : '처리 대기 중인 신고가 없습니다.';

  /// Status-edit console entry points (the consoles where operators change
  /// record state). Shell tabs reach the same routes; these are the dashboard's
  /// in-context shortcuts.
  List<AssenDashboardQuickAction> _quickActions(BuildContext context) {
    return <AssenDashboardQuickAction>[
      AssenDashboardQuickAction(
        icon: Icons.report_outlined,
        label: '신고 처리',
        onTap: () => context.go(OperatorRoutes.reports),
      ),
      AssenDashboardQuickAction(
        icon: Icons.calendar_month_outlined,
        label: '출근표',
        onTap: () => context.go(OperatorRoutes.schedule),
      ),
      AssenDashboardQuickAction(
        icon: Icons.how_to_reg_outlined,
        label: '체크인',
        onTap: () => context.go(OperatorRoutes.checkin),
      ),
      AssenDashboardQuickAction(
        icon: Icons.photo_camera_outlined,
        label: '체키',
        onTap: () => context.go(OperatorRoutes.cheki),
      ),
    ];
  }

  /// Admin-only sections (settings / permissions / risk / audit-log). Surfaced
  /// only for a manager viewer; each routes to the deep-link-only /admin slot.
  List<AssenDashboardQuickAction> _adminActions(BuildContext context) {
    return <AssenDashboardQuickAction>[
      AssenDashboardQuickAction(
        icon: Icons.settings_outlined,
        label: '설정',
        onTap: () => context.go(OperatorRoutes.admin),
      ),
      AssenDashboardQuickAction(
        icon: Icons.admin_panel_settings_outlined,
        label: '권한 관리',
        onTap: () => context.go(OperatorRoutes.admin),
      ),
      AssenDashboardQuickAction(
        icon: Icons.report_problem_outlined,
        label: '위험 고객',
        onTap: () => context.go(OperatorRoutes.admin),
      ),
      AssenDashboardQuickAction(
        icon: Icons.receipt_long_outlined,
        label: '감사 로그',
        onTap: () => context.go(OperatorRoutes.admin),
      ),
    ];
  }

  /// Copies the day's counts to the clipboard as CSV (counts only, no PII),
  /// then confirms via a snackbar. Real file save/share is a later concern.
  Future<void> _exportCsv(
    BuildContext context,
    OperatorDashboardMetrics metrics,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await Clipboard.setData(
        ClipboardData(text: dashboardMetricsCsv(metrics)),
      );
      messenger.showSnackBar(
        const SnackBar(content: Text('CSV를 클립보드에 복사했습니다.')),
      );
    } on Exception {
      messenger.showSnackBar(
        const SnackBar(content: Text('CSV 복사에 실패했습니다.')),
      );
    }
  }
}
