import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/creator/creator_controller.dart';
import 'package:assen_mobile/src/creator/creator_repository.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/membership/membership_section.dart';
import 'package:cached_network_image/cached_network_image.dart';
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
/// [AssenStatRow], and the bio — unless the caller has personally blocked the
/// creator ([Creator.blocked]), in which case a 차단 empty state replaces the
/// profile content (unblocking is a social/settings gate, not built here yet).
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
      body: AssenAsyncView<Creator>(
        value: profile,
        loading: const _ProfileSkeleton(),
        onRetry: () =>
            ref.read(creatorControllerProvider(handle).notifier).refresh(),
        // A 404 is a distinct "no such creator" state with a browse CTA, not
        // the generic retry; anything else falls through (null) to the default.
        errorBuilder: (error, _) => error is CreatorNotFoundException
            ? AssenErrorState(
                title: '없는 크리에이터예요',
                message: '@$handle 님을 찾지 못했어요. 주소를 다시 확인해 주세요.',
                retryLabel: '둘러보기로',
                onRetry: () => context.go(RoutePaths.discovery),
              )
            : null,
        data: (creator) => creator.blocked
            ? const AssenEmptyState(
                title: '차단한 크리에이터예요',
                message: '내가 차단한 크리에이터라 프로필을 표시하지 않아요.',
              )
            : _CreatorProfile(creator: creator),
      ),
    );
  }
}

/// The loaded profile: cover header, stats, an (auth-gated) follow button, and
/// bio.
class _CreatorProfile extends ConsumerWidget {
  const _CreatorProfile({required this.creator});

  final Creator creator;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    // Following is auth-gated: only a signed-in fan sees the follow button (the
    // server would 401 a write). A guest still browses the full public profile.
    final signedIn = ref.watch(authControllerProvider).isAuthenticated;
    final accent = CreatorAccent.fromHex(
      creator.accentColor,
      surface: colors.white,
      fallback: colors.indigo500,
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
          // Mirrors web `creator-home-header`: a creator with their own accent
          // gets that wash; a creator without one gets the sanctioned brand
          // gradient hero (tokens.md 2026-07-09 cover exception). A real cover
          // image always wins over both. brandScrimmed (not the plain brand
          // gradient) so this shared AssenCoverHeader cover stays AA-safe for
          // text/badges regardless of how a future caller uses its overlay
          // slots (2026-07-10 a11y fix).
          accent: creator.accentColor == null ? null : accent.accentContainer,
          gradient: creator.accentColor == null
              ? AssenGradients.brandScrimmed
              : null,
          coverImage: creator.coverUrl == null
              ? null
              : CachedNetworkImageProvider(creator.coverUrl!),
          coverSemanticLabel: '${creator.displayName} 커버 이미지',
          avatar: AssenAvatar(
            name: creator.displayName,
            size: AssenAvatarSize.l,
            imageProvider: creator.avatarUrl == null
                ? null
                : CachedNetworkImageProvider(creator.avatarUrl!),
            semanticLabel: '${creator.displayName} 프로필 사진',
          ),
          badge: creator.verified
              ? Semantics(
                  label: '인증된 크리에이터',
                  child: Icon(Icons.verified, color: accent.accent, size: 20),
                )
              : null,
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
          child: AssenStatRow(
            stats: [
              AssenStat(
                value: formatThousands(creator.followers),
                label: '팔로워',
              ),
              AssenStat(value: formatThousands(creator.posts), label: '게시물'),
            ],
          ),
        ),
        if (signedIn) ...[
          const SizedBox(height: SpacingTokens.s4),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
            child: AssenButton(
              label: creator.following ? '팔로잉' : '팔로우',
              style: creator.following
                  ? AssenButtonStyle.secondary
                  : AssenButtonStyle.primary,
              icon: creator.following ? Icons.check : Icons.add,
              expand: true,
              onPressed: () => ref
                  .read(creatorControllerProvider(creator.handle).notifier)
                  .toggleFollow(),
            ),
          ),
        ],
        if (creator.bio != null) ...[
          const SizedBox(height: SpacingTokens.s6),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s4),
            child: Text(
              creator.bio!,
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                height: 1.5,
                color: colors.ink600,
              ),
            ),
          ),
        ],
        // The creator's membership tiers (self-loading; silent when there are
        // none). Subscribing is a payment gate not built on mobile yet.
        MembershipSection(creatorId: creator.id),
      ],
    );
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
