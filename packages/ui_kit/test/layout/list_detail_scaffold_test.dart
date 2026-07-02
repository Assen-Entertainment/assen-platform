import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins [AssenListDetailScaffold] (ASS-147 Slice 3): below its breakpoint it is
/// the list alone (the caller pushes a detail route); at the breakpoint and
/// wider the list sits beside the detail pane. Widths come from the LOCAL
/// constraints so it composes inside a sidebar-shell body.
void _setSurface(WidgetTester tester, double width) {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = Size(width, 1000);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Widget _host({double? listPaneWidth}) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(
    body: AssenListDetailScaffold(
      listPaneWidth: listPaneWidth,
      list: const SizedBox(key: Key('list'), height: 200),
      detail: const SizedBox(key: Key('detail'), height: 200),
    ),
  ),
);

void main() {
  testWidgets('below the large breakpoint renders only the list', (
    tester,
  ) async {
    _setSurface(tester, 1000); // expanded, < large
    await tester.pumpWidget(_host());

    expect(find.byKey(const Key('list')), findsOneWidget);
    expect(find.byKey(const Key('detail')), findsNothing);
  });

  testWidgets('at large and wider the list sits left of the detail pane', (
    tester,
  ) async {
    _setSurface(tester, 1400); // large
    await tester.pumpWidget(_host());

    expect(find.byKey(const Key('list')), findsOneWidget);
    expect(find.byKey(const Key('detail')), findsOneWidget);

    final list = tester.getRect(find.byKey(const Key('list')));
    final detail = tester.getRect(find.byKey(const Key('detail')));
    expect(list.right, lessThanOrEqualTo(detail.left));
    // Side by side, not stacked: the panes overlap vertically.
    expect(list.top, lessThan(detail.bottom));
    expect(detail.top, lessThan(list.bottom));
  });

  testWidgets('a fixed listPaneWidth pins the list pane width', (tester) async {
    _setSurface(tester, 1400);
    await tester.pumpWidget(_host(listPaneWidth: 360));

    final list = tester.getRect(find.byKey(const Key('list')));
    expect(list.width, 360);
  });
}
