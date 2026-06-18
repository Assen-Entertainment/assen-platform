import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/shell/operator_shell.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the operator console shell at large/extra-large widths after the fan
/// redesign un-collapsed large/XL from [AssenWindowSize.expanded] (ASS-147
/// Slice 1). The operator app deliberately keeps the legacy
/// [AssenAdaptiveShell] (extended rail + 1440 console column) — it does NOT
/// adopt the new sidebar —
/// so this asserts the `>=`/atLeast migration left it byte-for-byte unchanged at
/// 1600 and 2560 (the existing operator_shell_test only covers up to 1280).
Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: child,
);

void _setLogicalSize(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 1000);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Widget _shell() => OperatorShell(
  currentIndex: 0,
  onDestinationSelected: (_) {},
  child: const SizedBox.expand(key: Key('operator-body')),
);

void _expectExtendedRailAndConsoleColumn(WidgetTester tester) {
  expect(find.byType(NavigationRail), findsOneWidget);
  final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
  expect(rail.extended, isTrue);

  final constrained = tester.widget<ConstrainedBox>(
    find.descendant(
      of: find.byType(AssenContentColumn),
      matching: find.byType(ConstrainedBox),
    ),
  );
  expect(constrained.constraints.maxWidth, AssenLayout.consoleContentMaxWidth);
}

void main() {
  group('OperatorShell stays on the legacy adaptive shell at large/XL', () {
    testWidgets('keeps the extended rail + 1440 console column at 1600', (
      tester,
    ) async {
      _setLogicalSize(tester, 1600);
      await tester.pumpWidget(_host(_shell()));
      _expectExtendedRailAndConsoleColumn(tester);
    });

    testWidgets('keeps the extended rail + 1440 console column at 2560', (
      tester,
    ) async {
      _setLogicalSize(tester, 2560);
      await tester.pumpWidget(_host(_shell()));
      _expectExtendedRailAndConsoleColumn(tester);
    });
  });
}
