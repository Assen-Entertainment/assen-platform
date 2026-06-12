import 'dart:ui' show Size;

import 'package:fan_app/app.dart';
import 'package:fan_app/state/favorite_cast_store.dart';
import 'package:features/features.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Pumps the full fan app with a shared mock auth repo, then signs in so the
/// favorite flow can cross the home, profile, and schedule shell branches.
Future<void> _pumpSignedInApp(WidgetTester tester) async {
  FanFavoriteStore.instance.resetToInitialState();
  addTearDown(FanFavoriteStore.instance.resetToInitialState);

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

/// Gives the home and schedule slivers enough room to build their cards.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets(
    'cast profile favorite toggle updates home and schedule surfaces',
    (tester) async {
      _useTallSurface(tester);
      await _pumpSignedInApp(tester);

      expect(find.byType(AssenCastProfileCard), findsOneWidget);
      expect(find.byTooltip('최애 해제'), findsOneWidget);

      await tester.tap(find.byType(AssenCastProfileCard).first);
      await tester.pumpAndSettle();

      expect(find.text('미오'), findsWidgets);
      await tester.tap(find.byTooltip('최애 해제'));
      await tester.pumpAndSettle();
      expect(find.byTooltip('최애 등록'), findsOneWidget);

      await tester.tap(find.byTooltip('뒤로'));
      await tester.pumpAndSettle();

      expect(find.text('아직 등록한 최애가 없어요'), findsOneWidget);
      expect(find.byType(AssenCastProfileCard), findsNothing);

      await tester.tap(find.text('출근표').last);
      await tester.pumpAndSettle();

      expect(find.byType(AssenCastProfileCard), findsNWidgets(3));
      expect(find.byTooltip('최애 해제'), findsNothing);
      expect(find.byTooltip('최애 등록'), findsNWidgets(3));

      await tester.tap(find.byType(AssenCastProfileCard).first);
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('최애 등록'));
      await tester.pumpAndSettle();
      expect(find.byTooltip('최애 해제'), findsOneWidget);

      await tester.tap(find.byTooltip('뒤로'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('홈').last);
      await tester.pumpAndSettle();

      expect(find.byType(AssenCastProfileCard), findsOneWidget);
      expect(find.byTooltip('최애 해제'), findsOneWidget);
    },
  );
}
