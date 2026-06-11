// Widget tests for AssenFilterChip / AssenTimeSlotChip. Pixel golden skipped
// pending #31.

import 'package:alchemist/alchemist.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: Center(child: child)),
);

BoxDecoration _decorationOf(WidgetTester tester) {
  final container = tester.widget<Container>(
    find
        .descendant(of: find.byType(InkWell), matching: find.byType(Container))
        .first,
  );
  return container.decoration! as BoxDecoration;
}

void main() {
  group('AssenFilterChip', () {
    testWidgets('renders its label and count', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenFilterChip(
            label: '체키',
            selected: true,
            count: 12,
            onSelected: (_) {},
          ),
        ),
      );
      expect(find.text('체키'), findsOneWidget);
      expect(find.text('12'), findsOneWidget);
    });

    testWidgets('selected fills with strawberry pastel', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenFilterChip(label: '체키', selected: true, onSelected: (_) {}),
        ),
      );
      expect(_decorationOf(tester).color, RefColors.strawberryBg);
    });

    testWidgets('reports toggled selection on tap', (tester) async {
      bool? next;
      await tester.pumpWidget(
        _host(
          AssenFilterChip(
            label: '게임',
            selected: false,
            onSelected: (v) => next = v,
          ),
        ),
      );
      await tester.tap(find.byType(AssenFilterChip));
      expect(next, isTrue);
    });
  });

  group('AssenTimeSlotChip', () {
    testWidgets('available slot is tappable', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenTimeSlotChip(
            label: '14:00',
            state: AssenTimeSlotState.available,
            onTap: () => taps++,
          ),
        ),
      );
      await tester.tap(find.byType(AssenTimeSlotChip));
      expect(taps, 1);
    });

    testWidgets('full slot ignores taps and strikes through', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          AssenTimeSlotChip(
            label: '15:00',
            state: AssenTimeSlotState.full,
            onTap: () => taps++,
          ),
        ),
      );
      await tester.tap(find.byType(AssenTimeSlotChip), warnIfMissed: false);
      expect(taps, 0);
      final text = tester.widget<Text>(find.text('15:00'));
      expect(text.style!.decoration, TextDecoration.lineThrough);
    });

    testWidgets('selected slot fills with the rose anchor', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenTimeSlotChip(
            label: '16:00',
            state: AssenTimeSlotState.selected,
            onTap: () {},
          ),
        ),
      );
      expect(_decorationOf(tester).color, RefColors.roseMain);
    });
  });

  goldenTest(
    'chips match the approved baseline',
    fileName: 'chips',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'filter-selected',
          child: AssenFilterChip(
            label: '체키',
            selected: true,
            count: 12,
            onSelected: (_) {},
          ),
        ),
        GoldenTestScenario(
          name: 'slot-available',
          child: AssenTimeSlotChip(
            label: '14:00',
            state: AssenTimeSlotState.available,
            onTap: () {},
          ),
        ),
        GoldenTestScenario(
          name: 'slot-full',
          child: const AssenTimeSlotChip(
            label: '15:00',
            state: AssenTimeSlotState.full,
            onTap: null,
          ),
        ),
      ],
    ),
  );
}
