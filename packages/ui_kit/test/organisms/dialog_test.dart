// Widget tests for AssenDialog. One/two-button layouts, destructive recolour,
// callbacks, and the show() presenter. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('AssenDialog', () {
    testWidgets('renders title, message and a single confirm', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenDialog(
            title: '알림',
            message: '저장되었습니다.',
            confirmLabel: '확인',
            onConfirm: () {},
          ),
        ),
      );
      expect(find.text('알림'), findsOneWidget);
      expect(find.text('저장되었습니다.'), findsOneWidget);
      expect(find.text('확인'), findsOneWidget);
      // No cancel label was given — only one button.
      expect(find.byType(TextButton), findsNothing);
    });

    testWidgets('two-button layout fires confirm and cancel', (tester) async {
      var confirm = 0;
      var cancel = 0;
      await tester.pumpWidget(
        _host(
          AssenDialog(
            title: '예약을 취소할까요?',
            confirmLabel: '취소하기',
            onConfirm: () => confirm++,
            cancelLabel: '닫기',
            onCancel: () => cancel++,
          ),
        ),
      );
      await tester.tap(find.text('닫기'));
      await tester.tap(find.text('취소하기'));
      expect(cancel, 1);
      expect(confirm, 1);
    });

    testWidgets('destructive confirm fills with the error red', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenDialog(
            title: '삭제할까요?',
            confirmLabel: '삭제',
            onConfirm: () {},
            destructive: true,
          ),
        ),
      );
      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      final bg = button.style!.backgroundColor!.resolve({});
      expect(bg, RefColors.redMain);
    });

    testWidgets('show() presents and returns its pop value', (tester) async {
      bool? result;
      await tester.pumpWidget(
        _host(
          Builder(
            builder: (context) => TextButton(
              onPressed: () async {
                result = await AssenDialog.show<bool>(
                  context,
                  dialog: AssenDialog(
                    title: '확인',
                    confirmLabel: '예',
                    onConfirm: () => Navigator.of(context).pop(true),
                  ),
                );
              },
              child: const Text('열기'),
            ),
          ),
        ),
      );
      await tester.tap(find.text('열기'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('예'));
      await tester.pumpAndSettle();
      expect(result, isTrue);
    });
  });

  goldenTest(
    'dialog matches the approved baseline',
    fileName: 'dialog',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'two-button',
          child: AssenDialog(
            title: '예약을 취소할까요?',
            message: '취소 후에는 되돌릴 수 없습니다.',
            confirmLabel: '취소하기',
            onConfirm: () {},
            cancelLabel: '닫기',
            onCancel: () {},
            destructive: true,
          ),
        ),
      ],
    ),
  );
}
