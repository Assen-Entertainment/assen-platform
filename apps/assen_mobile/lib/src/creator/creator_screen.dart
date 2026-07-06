import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/creator/creator_controller.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The creator profile screen, reached via the deep-linkable `/creator/:handle`
/// route.
///
/// Wired to `GET /api/creators/{handle}` through
/// [creatorControllerProvider]: it renders the three async states through
/// ui_kit only — a skeleton while loading, a dedicated "없는 크리에이터" state on
/// 404 ([CreatorNotFoundException]) and [AssenErrorState] (with retry) on any
/// other failure. On success it paints the [AssenCoverHeader] (cover wash
/// tinted by the creator's parsed [CreatorAccent]), the follower/post
/// [AssenStatRow], and the bio.
class CreatorScreen extends ConsumerWidget {
  /// Creates the profile screen for the creator identified by [handle].
  const CreatorScreen({required this.handle, super.key});

  /// The @-handle from the route path parameter.
  final String handle;

  void _back(BuildContext context) {
    // Deep links can open this with no back stack; fall back to the home tab.
    context.canPop() ? context.pop() : context.go(RoutePaths.discovery);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(creatorControllerProvider(handle));
    return Scaffold(
      appBar: AssenAppBar(title: '@$handle', onBack: () => _back(context)),
      body: profile.when(
        loading: () => const _ProfileSkeleton(),
        error: (error, stackTrace) => error is CreatorNotFoundException
            ? AssenErrorState(
                title: '없는 크리에이터예요',
                message: '@$handle 님을 찾지 못했어요. 주소를 다시 확인해 주세요.',
                retryLabel: '둘러보기로',
                onRetry: () => context.go(RoutePaths.discovery),
              )
            : AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () => ref
                    .read(creatorControllerProvider(handle).notifier)
                    .refresh(),
              ),
        data: (creator) => _CreatorProfile(creator: creator),
      ),
    );
  }
}

/// The loaded profile: cover header, stats, and bio.
class _CreatorProfile extends StatelessWidget {
  const _CreatorProfile({required this.creator});

  final Creator creator;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final accent = CreatorAccent.fromHex(
      creator.accentColor,
      surface: colors.white,
      fallback: colors.roseMain,
    );
    final subtitle =
        '@${creator.handle}'
        '${creator.category == null ? '' : ' · ${creator.category}'}';

    return ListView(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s8),
      children: [
        AssenCoverHeader(
          title: creator.displayName,
          subtitle: subtitle,
          accent: accent.accentContainer,
          coverImage: creator.coverUrl == null
              ? null
              : NetworkImage(creator.coverUrl!),
          avatar: AssenAvatar(
            name: creator.displayName,
            size: AssenAvatarSize.l,
            imageProvider: creator.avatarUrl == null
                ? null
                : NetworkImage(creator.avatarUrl!),
          ),
          badge: creator.verified
              ? Icon(Icons.verified, color: accent.accent, size: 20)
              : null,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
          child: AssenStatRow(
            stats: [
              AssenStat(value: _formatCount(creator.followers), label: '팔로워'),
              AssenStat(value: _formatCount(creator.posts), label: '게시물'),
            ],
          ),
        ),
        if (creator.bio != null) ...[
          const SizedBox(height: SpacingTokens.s6),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
            child: Text(
              creator.bio!,
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                height: 1.5,
                color: colors.ink700,
              ),
            ),
          ),
        ],
      ],
    );
  }

  /// Formats a count with thousands separators (e.g. `1,284`).
  static String _formatCount(int value) {
    final digits = value.toString();
    final buffer = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(',');
      buffer.write(digits[i]);
    }
    return buffer.toString();
  }
}

/// The loading state: a cover/avatar/stat skeleton standing in for the profile.
class _ProfileSkeleton extends StatelessWidget {
  const _ProfileSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: const [
        AssenSkeleton(width: double.infinity, height: 140, radius: 0),
        SizedBox(height: SpacingTokens.s4),
        Center(child: AssenSkeleton(width: 96, height: 96, radius: 48)),
        SizedBox(height: SpacingTokens.s3),
        Center(child: AssenSkeleton(width: 160)),
        SizedBox(height: SpacingTokens.s2),
        Center(child: AssenSkeleton(width: 220)),
        SizedBox(height: SpacingTokens.s6),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
          child: AssenSkeleton(width: double.infinity),
        ),
      ],
    );
  }
}
