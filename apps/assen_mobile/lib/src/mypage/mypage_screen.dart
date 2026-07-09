import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/mypage/mypage_controller.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 마이 (my page) tab: the signed-in fan's account summary.
///
/// Auth-gated — the router redirects signed-out viewers to the login wall
/// before this builds — so it always renders for an authenticated session,
/// wired to `GET /api/fan/me` through [myPageControllerProvider]. It shows the
/// fan identity (avatar + nickname + role/handle) and a sign-out action
/// (`AuthController.signOut`, which the router then bounces back to login).
/// Loading is a skeleton; a fetch failure falls back to [AssenErrorState].
class MyPageScreen extends ConsumerWidget {
  /// Creates the my-page tab.
  const MyPageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(myPageControllerProvider);
    return Scaffold(
      appBar: const AssenAppBar(title: '마이'),
      body: me.when(
        loading: () => const _MyPageSkeleton(),
        error: (error, stackTrace) => AssenErrorState(
          title: '불러오지 못했어요',
          message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
          onRetry: () => ref.read(myPageControllerProvider.notifier).refresh(),
        ),
        data: (fan) => _MyPageBody(fan: fan),
      ),
    );
  }
}

/// The loaded account view: identity header + sign-out.
class _MyPageBody extends ConsumerWidget {
  const _MyPageBody({required this.fan});

  final FanMe fan;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final subtitle = fan.handle == null ? fan.role : '@${fan.handle}';

    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: [
        Row(
          children: [
            AssenAvatar(
              name: fan.nickname,
              size: AssenAvatarSize.l,
              imageProvider: fan.avatarUrl == null
                  ? null
                  : CachedNetworkImageProvider(fan.avatarUrl!),
              semanticLabel: '${fan.nickname} 프로필 사진',
            ),
            const SizedBox(width: SpacingTokens.s4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    fan.nickname,
                    style: TextStyle(
                      fontSize: TypographyTokens.titleLSize,
                      fontWeight: FontWeight.w800,
                      color: colors.ink900,
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.s1),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: TypographyTokens.bodyMSize,
                      color: colors.ink500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.s6),
        AssenListItem(
          title: '주문 내역',
          leading: Icon(Icons.receipt_long_outlined, color: colors.ink600),
          onTap: () => context.go(RoutePaths.orders),
        ),
        AssenListItem(
          title: '스튜디오',
          leading: Icon(Icons.dashboard_outlined, color: colors.ink600),
          onTap: () => context.go(RoutePaths.studio),
        ),
        AssenListItem(
          title: '설정',
          leading: Icon(Icons.settings_outlined, color: colors.ink600),
          onTap: () => context.go(RoutePaths.settings),
        ),
        const SizedBox(height: SpacingTokens.s8),
        AssenButton(
          label: '로그아웃',
          style: AssenButtonStyle.secondary,
          expand: true,
          onPressed: () => ref.read(authControllerProvider.notifier).signOut(),
        ),
      ],
    );
  }
}

/// The loading state: an identity-header skeleton.
class _MyPageSkeleton extends StatelessWidget {
  const _MyPageSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Row(
        children: [
          AssenSkeleton(width: 72, height: 72, radius: 36),
          SizedBox(width: SpacingTokens.s4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AssenSkeleton(width: 140),
                SizedBox(height: SpacingTokens.s2),
                AssenSkeleton(width: 100),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
