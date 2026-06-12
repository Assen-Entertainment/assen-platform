import 'dart:ui' show Size;

import 'package:fan_app/screens/cast_profile_screen.dart';
import 'package:fan_app/state/favorite_cast_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

/// Gives the profile slivers enough vertical room to build the full profile.
void _useTallSurface(WidgetTester tester) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('cast profile shows approved intro, event, and cheki status', (
    tester,
  ) async {
    _useTallSurface(tester);
    FanFavoriteStore.instance.resetToInitialState();
    addTearDown(FanFavoriteStore.instance.resetToInitialState);

    await tester.pumpWidget(
      MaterialApp(
        theme: AssenTheme.light(),
        home: const CastProfileScreen(castId: 'yuki'),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('유키'), findsWidgets);
    expect(find.text('하늘빛 미소 · 노래 담당'), findsOneWidget);
    expect(
      find.text('차분한 노래와 포토 포즈 안내로 기념일 방문을 도와요.'),
      findsOneWidget,
    );
    expect(find.text('게스트데이 보컬 타임'), findsOneWidget);
    expect(find.text('체키 촬영 가능'), findsOneWidget);
    expect(find.text('동의된 프로필 정보만 공개 중'), findsOneWidget);
    expect(find.byTooltip('최애 등록'), findsOneWidget);
    expect(find.textContaining('DM'), findsNothing);
    expect(find.textContaining('댓글'), findsNothing);
  });
}
