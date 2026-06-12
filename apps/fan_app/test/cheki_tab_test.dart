import 'package:fan_app/app.dart';
import 'package:features/features.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps the full fan app with a shared mock auth repo, then signs in so the
/// protected 5-tab shell is reachable.
Future<void> _pumpSignedInApp(WidgetTester tester) async {
  final repo = MockAuthRepository();
  addTearDown(repo.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [authRepositoryProvider.overrideWithValue(repo)],
      child: const FanApp(),
    ),
  );
  await tester.pumpAndSettle();

  await repo.signIn(identifier: 'fan@x', password: 'pw');
  await tester.pumpAndSettle();
}

/// Gives the cheki grid enough room to build every lazy child in the shell.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('cheki tab renders the collected album grid in the fan shell', (
    tester,
  ) async {
    _useTallSurface(tester);
    await _pumpSignedInApp(tester);

    await tester.tap(find.text('체키').last);
    await tester.pumpAndSettle();

    expect(find.byType(AssenTabBar), findsOneWidget);
    expect(find.text('체키 앨범'), findsOneWidget);
    expect(find.text('6 / 12'), findsOneWidget);
    expect(find.byType(AssenProgressBar), findsOneWidget);
    expect(find.byType(AssenChekiFrame), findsNWidgets(6));
    expect(find.byType(AssenCollectionCell), findsNWidgets(3));
    expect(find.byType(AssenEmptyState), findsNothing);
  });
}
