import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/mock/fan_mock_data.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The my-page hub tab (F1) — a simple placeholder hub (no template yet).
///
/// Lists the account sub-surfaces (쿠폰함/포인트/알림/신고 — built later) as
/// [AssenListItem] rows, plus a 로그아웃 action wired to the shared auth. Signing
/// out clears the session; the router guard then redirects to /login (the same
/// transition the expired-session path takes — CONSTRAINTS #31). The QR row is
/// a live deep link to /qr.
class MyScreen extends ConsumerWidget {
  /// Creates the my-page hub.
  const MyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    const member = FanMockData.member;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '마이'),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s4),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s2,
              SpacingTokens.screenMargin,
              SpacingTokens.s4,
            ),
            child: Row(
              children: [
                AssenAvatar(
                  name: member.name,
                  hue: AssenBadgeHue.strawberry,
                  size: AssenAvatarSize.l,
                ),
                const SizedBox(width: SpacingTokens.s4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        member.name,
                        style: TypographyTokens.titleL.copyWith(
                          fontWeight: FontWeight.w800,
                          color: colors.ink900,
                        ),
                      ),
                      const SizedBox(height: SpacingTokens.s1),
                      Text(
                        '${member.tierLabel} · ${member.memberNumber}',
                        style: TypographyTokens.label.copyWith(
                          color: colors.ink700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          AssenListItem(
            title: '회원증 QR',
            leading: Icon(Icons.qr_code_2, color: colors.ink700),
            onTap: () => context.push(FanRoutes.qr),
          ),
          AssenListItem(
            title: '쿠폰함',
            leading: Icon(
              Icons.confirmation_number_outlined,
              color: colors.ink700,
            ),
            onTap: () {},
          ),
          AssenListItem(
            title: '포인트 내역',
            leading: Icon(Icons.toll_outlined, color: colors.ink700),
            onTap: () {},
          ),
          AssenListItem(
            title: '알림 설정',
            leading: Icon(Icons.notifications_none, color: colors.ink700),
            onTap: () {},
          ),
          AssenListItem(
            title: '신고하기',
            leading: Icon(Icons.flag_outlined, color: colors.ink700),
            onTap: () {},
          ),
          const SizedBox(height: SpacingTokens.s4),
          AssenListItem(
            title: '로그아웃',
            showChevron: false,
            leading: Icon(Icons.logout, color: colors.redInk),
            onTap: () => ref.read(authSessionProvider.notifier).signOut(),
          ),
        ],
      ),
    );
  }
}
