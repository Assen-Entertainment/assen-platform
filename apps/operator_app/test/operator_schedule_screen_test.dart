import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/schedule/operator_schedule_providers.dart';
import 'package:operator_app/schedule/operator_schedule_repository.dart';
import 'package:operator_app/screens/operator_schedule_screen.dart';
import 'package:ui_kit/ui_kit.dart';

/// Anchors the mock so the seeded dates (today / tomorrow) are deterministic.
final DateTime _fixedNow = DateTime(2026, 6, 14, 10);

Future<void> _pump(WidgetTester tester, {int? operatorId}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        operatorScheduleRepositoryProvider.overrideWithValue(
          InMemoryOperatorScheduleRepository(now: _fixedNow),
        ),
        if (operatorId != null)
          currentOperatorIdProvider.overrideWithValue(operatorId),
      ],
      child: MaterialApp(
        theme: AssenTheme.light(),
        home: const OperatorScheduleScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

/// Switches to the 변경 로그 view.
Future<void> _openChangeLog(WidgetTester tester) async {
  await tester.tap(find.text('변경 로그'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('board shows the first date entries with status badges', (
    tester,
  ) async {
    await _pump(tester);

    expect(find.text('출근표 관리'), findsOneWidget);
    // Default date = today (6/14): 미오 published + 유키 draft.
    expect(find.text('미오'), findsOneWidget);
    expect(find.text('유키'), findsOneWidget);
    expect(find.text('게시됨'), findsOneWidget);
    expect(find.text('초안'), findsOneWidget);
    expect(find.text('12:00–18:00'), findsOneWidget); // 미오
    // Tomorrow's casts are on the other date, not the board yet.
    expect(find.text('모카'), findsNothing);
    expect(find.text('베리'), findsNothing);
    expect(find.textContaining('다른 운영자의 승인'), findsOneWidget);
  });

  testWidgets('switching the date strip shows the other day', (tester) async {
    await _pump(tester);

    await tester.tap(find.textContaining('6/15'));
    await tester.pumpAndSettle();

    expect(find.text('모카'), findsOneWidget);
    expect(find.text('베리'), findsOneWidget);
    expect(find.text('비공개'), findsOneWidget); // 베리 unpublished
    expect(find.text('미오'), findsNothing);
  });

  testWidgets('adding a draft lands it on the board', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('초안 추가'));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, '캐스트'), '하나');
    await tester.enterText(
      find.widgetWithText(TextField, '시작 (HH:MM)'),
      '15:00',
    );
    await tester.enterText(
      find.widgetWithText(TextField, '종료 (HH:MM)'),
      '20:00',
    );
    await tester.tap(find.widgetWithText(FilledButton, '추가'));
    await tester.pumpAndSettle();

    expect(find.text('초안을 추가했습니다.'), findsOneWidget);
    expect(find.text('하나'), findsOneWidget);
    expect(find.text('15:00–20:00'), findsOneWidget);
    // 유키 (seed draft) + 하나 (new draft) both read 초안.
    expect(find.text('초안'), findsNWidgets(2));
  });

  testWidgets('a bad shift time is rejected by the create form', (
    tester,
  ) async {
    await _pump(tester);

    await tester.tap(find.text('초안 추가'));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, '캐스트'), '하나');
    await tester.enterText(
      find.widgetWithText(TextField, '시작 (HH:MM)'),
      '25:99',
    );
    await tester.tap(find.widgetWithText(FilledButton, '추가'));
    await tester.pumpAndSettle();

    expect(find.text('시간 형식은 HH:MM이어야 합니다.'), findsOneWidget);
    expect(find.text('초안을 추가했습니다.'), findsNothing);
  });

  testWidgets('publishing a draft flips its status badge', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('유키')); // draft entry card
    await tester.pumpAndSettle();
    expect(find.widgetWithText(FilledButton, '게시'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, '게시'));
    await tester.pumpAndSettle();

    expect(find.text('게시했습니다.'), findsOneWidget);
    // 미오 + 유키 are both published now; no draft remains on this date.
    expect(find.text('게시됨'), findsNWidgets(2));
    expect(find.text('초안'), findsNothing);
  });

  testWidgets('editing a draft updates its shift window', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('유키'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, '수정'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextField, '종료 (HH:MM)'),
      '21:00',
    );
    await tester.tap(find.widgetWithText(FilledButton, '저장'));
    await tester.pumpAndSettle();

    expect(find.text('초안을 수정했습니다.'), findsOneWidget);
    // Close the still-open detail dialog, then read the updated board card.
    await tester.tap(find.widgetWithText(TextButton, '닫기'));
    await tester.pumpAndSettle();
    expect(find.text('13:00–21:00'), findsOneWidget);
  });

  testWidgets('unpublishing a published entry hides it (비공개)', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('미오')); // published entry
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, '비공개'));
    await tester.pumpAndSettle();

    expect(find.text('비공개로 전환했습니다.'), findsOneWidget);
    expect(find.text('비공개'), findsOneWidget); // 미오 now unpublished
  });

  testWidgets('requesting a change on a published entry files it pending', (
    tester,
  ) async {
    await _pump(tester);

    await tester.tap(find.text('미오'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, '변경 요청'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextField, '종료 (HH:MM)'),
      '20:00',
    );
    await tester.enterText(find.widgetWithText(TextField, '사유 (선택)'), '연장');
    await tester.tap(find.widgetWithText(FilledButton, '변경 요청'));
    await tester.pumpAndSettle();

    expect(find.text('변경 요청을 제출했습니다.'), findsOneWidget);
    // Close the still-open detail dialog before navigating to the log.
    await tester.tap(find.widgetWithText(TextButton, '닫기'));
    await tester.pumpAndSettle();

    await _openChangeLog(tester);
    // Two seeded pending + the new one.
    expect(find.text('승인 대기'), findsNWidgets(3));
    expect(find.textContaining('18:00 → 20:00'), findsOneWidget);
  });

  testWidgets('a no-op change request is rejected by the form', (tester) async {
    await _pump(tester);

    await tester.tap(find.text('미오'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(TextButton, '변경 요청'));
    await tester.pumpAndSettle();

    // Submit without touching any prefilled field.
    await tester.tap(find.widgetWithText(FilledButton, '변경 요청'));
    await tester.pumpAndSettle();

    expect(find.text('변경된 내용이 없습니다.'), findsOneWidget);
  });

  testWidgets('the change log lists seeded changes with their status', (
    tester,
  ) async {
    await _pump(tester);
    await _openChangeLog(tester);

    expect(find.text('승인 대기'), findsNWidgets(2)); // change-1, change-2
    expect(find.text('승인됨'), findsOneWidget); // change-3 (history)
    expect(find.textContaining('12:00 → 13:00'), findsOneWidget); // change-1
  });

  testWidgets('the change log shows requester/decider attribution', (
    tester,
  ) async {
    await _pump(tester);
    await _openChangeLog(tester);

    // change-1 and change-3 were both filed by operator #2.
    expect(find.textContaining('요청: 운영자 #2'), findsWidgets);
    // Only the decided change (change-3) carries a decider + decision note.
    expect(find.textContaining('결정: 운영자 #1'), findsOneWidget);
    expect(find.textContaining('확인 완료'), findsOneWidget);
  });

  testWidgets('self-requested change disables its approve button', (
    tester,
  ) async {
    await _pump(tester); // current operator #1; change-2 was filed by #1

    await _openChangeLog(tester);

    // The self notice is shown for the operator's own pending request.
    expect(find.textContaining('다른 운영자가 승인해야'), findsOneWidget);

    final approveButtons = find.widgetWithText(FilledButton, '승인');
    expect(approveButtons, findsNWidgets(2));
    // Newest first: change-2 (self) is index 0 — disabled; change-1 enabled.
    expect(tester.widget<FilledButton>(approveButtons.at(0)).onPressed, isNull);
    expect(
      tester.widget<FilledButton>(approveButtons.at(1)).onPressed,
      isNotNull,
    );
  });

  testWidgets("approving another operator's change applies it", (tester) async {
    await _pump(tester);
    await _openChangeLog(tester);

    // change-1 (filed by #2) is the second pending card — approvable by #1.
    final approve = find.widgetWithText(FilledButton, '승인').at(1);
    await tester.ensureVisible(approve);
    await tester.pumpAndSettle();
    await tester.tap(approve);
    await tester.pumpAndSettle();

    expect(find.text('변경을 승인했습니다.'), findsOneWidget);
    // change-1 joins change-3 as approved; only change-2 stays pending.
    expect(find.text('승인됨'), findsNWidgets(2));
    expect(find.text('승인 대기'), findsOneWidget);
  });

  testWidgets('rejecting a pending change marks it 거부됨', (tester) async {
    await _pump(tester);
    await _openChangeLog(tester);

    await tester.tap(find.widgetWithText(TextButton, '거부').at(0));
    await tester.pumpAndSettle();

    expect(find.text('변경을 거부했습니다.'), findsOneWidget);
    expect(find.text('거부됨'), findsOneWidget);
    expect(find.text('승인 대기'), findsOneWidget); // change-1 still pending
  });

  testWidgets('the status filter narrows the change log (enum-limited)', (
    tester,
  ) async {
    await _pump(tester);
    await _openChangeLog(tester);

    // Open the filter and pick 거부됨 (no seeded rows match).
    await tester.tap(find.text('전체'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('거부됨').last);
    await tester.pumpAndSettle();

    expect(find.text('해당 상태의 변경 요청이 없습니다.'), findsOneWidget);
    expect(find.text('승인 대기'), findsNothing);
  });
}
