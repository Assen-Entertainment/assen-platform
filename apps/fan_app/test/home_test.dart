import 'package:fan_app/screens/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Hosts [HomeScreen] in a router exposing the routes its actions navigate to,
/// so the wiring (회원증 QR -> /qr, 캐스트 -> /cast/:id) is exercisable.
Widget _host() {
  final router = GoRouter(
    initialLocation: '/home',
    routes: [
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/qr',
        builder: (context, state) =>
            const Scaffold(body: Center(child: Text('QR_STUB'))),
      ),
      GoRoute(
        path: '/cast/:id',
        builder: (context, state) => Scaffold(
          body: Center(child: Text('CAST_${state.pathParameters['id']}')),
        ),
      ),
    ],
  );
  return MaterialApp.router(theme: AssenTheme.light(), routerConfig: router);
}

/// Gives the test view a tall surface so the whole scrolling home body lays
/// out (the lower slivers — calendar, cast card, banner — are otherwise below
/// the 800×600 default fold and not built by the lazy sliver list).
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('home composes the signature surfaces', (tester) async {
    _useTallSurface(tester);
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    expect(find.byType(AssenMembershipCard), findsOneWidget);
    expect(find.byType(AssenStampCard), findsOneWidget);
    expect(find.byType(AssenScheduleCalendar), findsOneWidget);
    expect(find.byType(AssenBannerCard), findsOneWidget);
    // Unified mock identity surfaces on the card.
    expect(find.text('체리체리'), findsOneWidget);
  });

  testWidgets('tapping a cast card deep-links to /cast/:id', (tester) async {
    _useTallSurface(tester);
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AssenCastProfileCard).first);
    await tester.pumpAndSettle();

    expect(find.text('CAST_mio'), findsOneWidget);
  });
}
