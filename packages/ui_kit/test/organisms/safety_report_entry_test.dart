// Widget tests for AssenSafetyReportEntry + AssenSafetyReportTypeList. Entry
// cell tap, the nine report types, and type selection. Golden skip #31.

import 'package:alchemist/alchemist.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: Center(child: SizedBox(width: 360, child: child)),
  ),
);

void main() {
  group('AssenSafetyReportEntry', () {
    testWidgets('renders the default copy and fires onTap', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(AssenSafetyReportEntry(onTap: () => taps++)),
      );
      expect(find.text('안전 신고하기'), findsOneWidget);
      await tester.tap(find.text('안전 신고하기'));
      expect(taps, 1);
    });
  });

  group('AssenSafetyReportTypeList', () {
    testWidgets('renders all nine report types', (tester) async {
      await tester.pumpWidget(
        _host(AssenSafetyReportTypeList(onSelect: (_) {})),
      );
      expect(
        find.byType(InkWell),
        findsNWidgets(AssenSafetyReportType.values.length),
      );
      expect(AssenSafetyReportType.values.length, 9);
      // Spot-check a couple of the type labels.
      expect(find.text('성희롱·성추행'), findsOneWidget);
      expect(find.text('기타'), findsOneWidget);
    });

    testWidgets('reports the tapped type', (tester) async {
      AssenSafetyReportType? picked;
      await tester.pumpWidget(
        _host(
          AssenSafetyReportTypeList(onSelect: (t) => picked = t),
        ),
      );
      await tester.tap(find.text('스토킹·따라다님'));
      expect(picked, AssenSafetyReportType.stalking);
    });

    testWidgets('marks the selected type with a check', (tester) async {
      await tester.pumpWidget(
        _host(
          AssenSafetyReportTypeList(
            selected: AssenSafetyReportType.privacy,
            onSelect: (_) {},
          ),
        ),
      );
      expect(find.byIcon(Icons.check), findsOneWidget);
    });
  });

  goldenTest(
    'safety report entry matches the approved baseline',
    fileName: 'safety_report_entry',
    skip: true, // 베이스라인 인간 승인 대기 (#31)
    builder: () => GoldenTestGroup(
      children: [
        GoldenTestScenario(
          name: 'entry',
          child: SizedBox(
            width: 360,
            child: AssenSafetyReportEntry(onTap: () {}),
          ),
        ),
      ],
    ),
  );
}
