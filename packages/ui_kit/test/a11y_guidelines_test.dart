// Automated accessibility-guideline coverage for the interactive ui_kit
// widgets (R10, ASS-249): Material 48dp / iOS 44pt tap targets, labelled tap
// targets, and text contrast. These lock the a11y policy so a later change that
// shrinks a hit area or drops a tappable label fails CI.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('ui_kit a11y guidelines', () {
    testWidgets('AssenIconButton meets tap-target + label guidelines', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _host(
          Center(
            child: AssenIconButton(
              icon: Icons.close,
              semanticLabel: '닫기',
              onPressed: () {},
            ),
          ),
        ),
      );
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });

    testWidgets('AssenListItem meets tap-target + label guidelines', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _host(
          AssenListItem(
            title: '설정',
            subtitle: '@mio',
            leading: const AssenAvatar(name: '미오'),
            onTap: () {},
          ),
        ),
      );
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });

    testWidgets('AssenPostCard meets tap-target + label + contrast', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _host(
          AssenPostCard(
            creatorName: '미오',
            creatorMeta: '@mio',
            timeLabel: '3분 전',
            verified: true,
            avatar: const AssenAvatar(name: '미오'),
            body: '오늘 방송 고마웠어요!',
            likeCount: 128,
            commentCount: 16,
            onTap: () {},
          ),
        ),
      );
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      await expectLater(tester, meetsGuideline(textContrastGuideline));
      handle.dispose();
    });

    testWidgets('AssenProductCard meets tap-target + label guidelines', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        _host(
          Center(
            child: SizedBox(
              width: 320,
              child: AssenProductCard(
                title: '한정 아크릴 스탠드',
                priceLabel: '₩18,000',
                tagLabel: '굿즈',
                meta: '선착순 100개',
                onTap: () {},
              ),
            ),
          ),
        ),
      );
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });
  });
}
