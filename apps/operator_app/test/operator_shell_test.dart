import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/shell/operator_shell.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: child,
);

void _setLogicalSize(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 900);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

Widget _shell({int currentIndex = 0}) => OperatorShell(
  currentIndex: currentIndex,
  onDestinationSelected: (_) {},
  child: const SizedBox.expand(key: Key('operator-body')),
);

void main() {
  group('OperatorShell', () {
    testWidgets('uses the bottom tab bar at compact width', (tester) async {
      _setLogicalSize(tester, 390);

      await tester.pumpWidget(_host(_shell()));

      expect(find.byType(AssenTabBar), findsOneWidget);
      expect(find.byType(NavigationRail), findsNothing);
    });

    testWidgets('uses a collapsed navigation rail at medium width', (
      tester,
    ) async {
      _setLogicalSize(tester, 768);

      await tester.pumpWidget(_host(_shell()));

      expect(find.byType(NavigationRail), findsOneWidget);
      expect(find.byType(AssenTabBar), findsNothing);
      final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
      expect(rail.extended, isFalse);
    });

    testWidgets(
      'uses an extended rail and the wider console column at expanded '
      'width',
      (tester) async {
        _setLogicalSize(tester, 1280);

        await tester.pumpWidget(_host(_shell(currentIndex: 1)));

        final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
        expect(rail.extended, isTrue);

        // The console is a working surface, so it uses the wider console column
        // rather than the fan reading column.
        final constrained = tester.widget<ConstrainedBox>(
          find.descendant(
            of: find.byType(AssenContentColumn),
            matching: find.byType(ConstrainedBox),
          ),
        );
        expect(
          constrained.constraints.maxWidth,
          AssenLayout.consoleContentMaxWidth,
        );
      },
    );

    testWidgets('renders every console destination in the extended rail', (
      tester,
    ) async {
      _setLogicalSize(tester, 1280);

      await tester.pumpWidget(_host(_shell()));

      for (final item in OperatorShell.destinations) {
        expect(find.text(item.label), findsOneWidget);
      }
    });
  });
}
