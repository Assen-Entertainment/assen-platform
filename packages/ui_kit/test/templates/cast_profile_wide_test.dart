import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pins the wide (expanded+) cast profile layout (ASS-147 Slice 2b): a
/// reading-width-capped supporting pane with the profile + 출근 일정 as the main
/// pane and the 체키 collection as the supporting rail. The existing
/// cast_profile_template_test pumps at the default (medium) surface and so it
/// keeps covering the stacked compact path.
Widget _host() => MaterialApp(
  theme: AssenTheme.light(),
  home: const AssenCastProfileTemplate(),
);

void _setSurface(WidgetTester tester, Size size) {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('at 1600 the profile/schedule main sits left of the 체키 rail', (
    tester,
  ) async {
    _setSurface(tester, const Size(1600, 1200));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    final calendar = tester.getRect(find.byType(AssenScheduleCalendar));
    final cheki = tester.getRect(find.byType(AssenCollectionCell).first);

    // Supporting pane: the schedule (main pane) is entirely left of the 체키
    // collection (right rail). Horizontal separation proves the two panes sit
    // side by side, not stacked (the compact test below proves stacking).
    expect(calendar.right, lessThanOrEqualTo(cheki.left));
  });

  testWidgets('at 800 the 체키 collection stacks below the schedule', (
    tester,
  ) async {
    _setSurface(tester, const Size(800, 3000));
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    final calendar = tester.getRect(find.byType(AssenScheduleCalendar));
    final cheki = tester.getRect(find.byType(AssenCollectionCell).first);
    expect(cheki.top, greaterThan(calendar.bottom));
  });
}
