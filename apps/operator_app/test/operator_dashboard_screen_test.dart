import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:operator_app/dashboard/operator_dashboard_providers.dart';
import 'package:operator_app/dashboard/operator_dashboard_repository.dart';
import 'package:operator_app/screens/operator_dashboard_screen.dart';
import 'package:ui_kit/ui_kit.dart';

/// Anchors the mock so the business day is deterministic.
final DateTime _fixedNow = DateTime(2026, 6, 15, 10);

/// A stub destination that names the route it stands in for.
GoRoute _marker(String path, String label) =>
    GoRoute(path: path, builder: (_, _) => Text(label));

Future<void> _pump(WidgetTester tester, {DashboardViewerRole? role}) async {
  // A surface tall enough that the whole scrolling dashboard (incl. the bottom
  // 관리 section) lays out, so an absent section is genuinely absent — not just
  // unbuilt off-screen.
  tester.view.physicalSize = const Size(1125, 9000);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final router = GoRouter(
    initialLocation: '/dashboard',
    routes: [
      GoRoute(
        path: '/dashboard',
        builder: (_, _) => const OperatorDashboardScreen(),
      ),
      _marker('/reports', 'reports-marker'),
      _marker('/schedule', 'schedule-marker'),
      _marker('/checkin', 'checkin-marker'),
      _marker('/cheki', 'cheki-marker'),
      _marker('/admin', 'admin-marker'),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        operatorDashboardRepositoryProvider.overrideWithValue(
          InMemoryOperatorDashboardRepository(now: _fixedNow),
        ),
        if (role != null) dashboardViewerRoleProvider.overrideWithValue(role),
      ],
      child: MaterialApp.router(
        theme: AssenTheme.light(),
        routerConfig: router,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the stat grid shows the live counts and business day', (
    tester,
  ) async {
    await _pump(tester);

    expect(find.byType(AssenStatCard), findsNWidgets(5));
    expect(find.text('38'), findsOneWidget); // visits
    expect(find.text('12'), findsOneWidget); // reservations
    expect(find.text('27'), findsOneWidget); // cheki
    expect(find.text('9'), findsOneWidget); // favorites
    expect(find.text('1'), findsOneWidget); // safety_reports_open
    expect(find.text('2026-06-15 기준'), findsOneWidget);
    expect(find.text('신고 1건이 처리 대기 중입니다.'), findsOneWidget);
  });

  testWidgets('tapping the 신고 notice opens the reports console', (
    tester,
  ) async {
    await _pump(tester);

    await tester.tap(find.text('신고 1건이 처리 대기 중입니다.'));
    await tester.pumpAndSettle();

    expect(find.text('reports-marker'), findsOneWidget);
  });

  testWidgets('a status-edit entry point opens the schedule console', (
    tester,
  ) async {
    await _pump(tester);

    expect(find.text('바로가기'), findsOneWidget);
    await tester.tap(find.widgetWithText(OutlinedButton, '출근표'));
    await tester.pumpAndSettle();

    expect(find.text('schedule-marker'), findsOneWidget);
  });

  testWidgets('the CSV export copies counts to the clipboard and confirms', (
    tester,
  ) async {
    final copied = <String>[];
    final messenger = tester.binding.defaultBinaryMessenger
      ..setMockMethodCallHandler(SystemChannels.platform, (call) async {
        if (call.method == 'Clipboard.setData') {
          copied.add((call.arguments as Map)['text'] as String);
        }
        return null;
      });
    addTearDown(
      () => messenger.setMockMethodCallHandler(SystemChannels.platform, null),
    );

    await _pump(tester);
    await tester.tap(find.byIcon(Icons.download_outlined));
    await tester.pumpAndSettle();

    expect(find.text('CSV를 클립보드에 복사했습니다.'), findsOneWidget);
    expect(copied, hasLength(1));
    // Counts only — header + value row, no names/prices.
    expect(copied.single, contains('business_day,visits'));
    expect(copied.single, contains('2026-06-15,38,27,12,9,1'));
  });

  testWidgets('admin sections are hidden for the default operator viewer', (
    tester,
  ) async {
    await _pump(tester); // no role override -> fail-closed operator default

    expect(find.text('관리'), findsNothing);
    expect(find.text('설정'), findsNothing);
    expect(find.text('감사 로그'), findsNothing);
  });

  testWidgets('admin sections appear for a manager and route to /admin', (
    tester,
  ) async {
    await _pump(tester, role: DashboardViewerRole.manager);

    expect(find.text('관리'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);
    expect(find.text('권한 관리'), findsOneWidget);
    expect(find.text('위험 고객'), findsOneWidget);
    expect(find.text('감사 로그'), findsOneWidget);

    await tester.tap(find.text('감사 로그'));
    await tester.pumpAndSettle();

    expect(find.text('admin-marker'), findsOneWidget);
  });
}
