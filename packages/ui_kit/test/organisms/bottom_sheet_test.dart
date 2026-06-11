// Widget tests for AssenBottomSheet (Korean B2C convention #2). Handle, title,
// body, optional pinned CTA, and the show() presenter. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenBottomSheet', () {
    testWidgets('renders the title and body', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenBottomSheet(
            title: '정렬 기준',
            child: Text('최신순'),
          ),
        ),
      );
      expect(find.text('정렬 기준'), findsOneWidget);
      expect(find.text('최신순'), findsOneWidget);
    });

    testWidgets('shows the pinned CTA only when given', (tester) async {
      await tester.pumpWidget(
        _host(const AssenBottomSheet(child: Text('내용'))),
      );
      expect(find.byType(AssenBottomCta), findsNothing);

      await tester.pumpWidget(
        _host(
          AssenBottomSheet(
            primaryLabel: '적용',
            onPrimary: () {},
            child: const Text('내용'),
          ),
        ),
      );
      expect(find.byType(AssenBottomCta), findsOneWidget);
      expect(find.text('적용'), findsOneWidget);
    });

    testWidgets('show() presents the sheet and returns its pop value', (
      tester,
    ) async {
      String? result;
      await tester.pumpWidget(
        _host(
          Builder(
            builder: (context) => Center(
              child: TextButton(
                onPressed: () async {
                  result = await AssenBottomSheet.show<String>(
                    context,
                    sheet: AssenBottomSheet(
                      title: '필터',
                      child: TextButton(
                        onPressed: () => Navigator.of(context).pop('done'),
                        child: const Text('닫기'),
                      ),
                    ),
                  );
                },
                child: const Text('열기'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('열기'));
      await tester.pumpAndSettle();
      expect(find.text('필터'), findsOneWidget);

      await tester.tap(find.text('닫기'));
      await tester.pumpAndSettle();
      expect(result, 'done');
    });
  });

  goldenTest(
    'bottom sheet matches the approved baseline',
    fileName: 'bottom_sheet',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'with-cta',
          child: SizedBox(
            width: 360,
            child: AssenBottomSheet(
              title: '정렬 기준',
              primaryLabel: '적용',
              onPrimary: () {},
              child: const Text('최신순'),
            ),
          ),
        ),
      ],
    ),
  );
}
