// Widget tests for AssenToast (성공 / 오류 / 정보). The info kind backs the Korean
// B2C convention #4 push-toggle change notice. show() pushes a SnackBar.
// Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenToast', () {
    testWidgets('renders the message and success glyph', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenToast(
            message: '완료되었습니다.',
            kind: AssenToastKind.success,
          ),
        ),
      );
      expect(find.text('완료되었습니다.'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });

    testWidgets('fires the action on tap', (tester) async {
      var undone = false;
      await tester.pumpWidget(
        _host(
          AssenToast(
            message: '삭제했습니다.',
            actionLabel: '실행취소',
            onAction: () => undone = true,
          ),
        ),
      );
      await tester.tap(find.text('실행취소'));
      expect(undone, isTrue);
    });

    testWidgets('show() surfaces a SnackBar', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AssenTheme.light(),
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => AssenToast.show(
                  context,
                  const AssenToast(message: '알림 설정이 변경되었습니다.'),
                ),
                child: const Text('show'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('show'));
      await tester.pump();
      expect(find.text('알림 설정이 변경되었습니다.'), findsOneWidget);
    });
  });

  goldenTest(
    'toast matches the approved baseline',
    fileName: 'toast',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'info',
          child: const SizedBox(
            width: 320,
            child: AssenToast(message: '광고성 알림 수신 설정이 변경되었습니다.'),
          ),
        ),
      ],
    ),
  );
}
