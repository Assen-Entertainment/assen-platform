import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/studio/studio_controller.dart';
import 'package:assen_mobile/src/studio/studio_repository.dart';
import 'package:assen_mobile/src/studio/studio_stats.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 스튜디오 screen: the signed-in creator owner's dashboard counts.
///
/// Wired to `GET /api/studio/stats` through [studioControllerProvider]. Two
/// unauthorized states are handled distinctly: a 401
/// ([StudioAuthRequiredException]) renders the "로그인이 필요해요" prompt (the app
/// ships signed-out), while a 403 ([StudioOwnerRequiredException]) — a
/// signed-in fan who owns no creator — renders the "크리에이터 전용" state.
/// A creator owner sees the six dashboard metrics; other failures fall back to
/// [AssenErrorState] with retry. Counts only — no revenue/settlement figure.
class StudioScreen extends ConsumerWidget {
  /// Creates the studio screen.
  const StudioScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.mypage);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(studioControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '스튜디오', onBack: () => _back(context)),
      body: AssenAsyncView<StudioStats>(
        value: stats,
        loading: const _StudioSkeleton(),
        onRetry: () => ref.read(studioControllerProvider.notifier).refresh(),
        // Two unauthorized states are not failures: a 401 shows the login wall,
        // a 403 (signed-in non-owner) the creator-only notice. Anything else
        // falls through (null) to the default error state.
        errorBuilder: (error, _) => switch (error) {
          StudioAuthRequiredException() => AssenEmptyState(
            title: '로그인이 필요해요',
            message: '스튜디오를 보려면 먼저 로그인해 주세요.',
            actionLabel: '로그인',
            onAction: () => context.go(RoutePaths.login),
          ),
          StudioOwnerRequiredException() => const AssenEmptyState(
            title: '크리에이터 전용이에요',
            message: '스튜디오는 크리에이터 계정에서만 볼 수 있어요.',
          ),
          _ => null,
        },
        data: (stats) => _StudioDashboard(stats: stats),
      ),
    );
  }
}

/// The loaded dashboard: the six studio metrics as a responsive card grid.
class _StudioDashboard extends StatelessWidget {
  const _StudioDashboard({required this.stats});

  final StudioStats stats;

  @override
  Widget build(BuildContext context) {
    final metrics = <(String, int)>[
      ('팔로워', stats.followers),
      ('게시물', stats.posts),
      ('상품', stats.products),
      ('판매중', stats.productsSelling),
      ('주문', stats.orders),
      ('구독자', stats.subscribers),
    ];
    return SingleChildScrollView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      child: AssenFeedGrid(
        minColumnWidth: 150,
        maxColumns: 2,
        columnSpacing: SpacingTokens.s3,
        rowSpacing: SpacingTokens.s3,
        children: [
          for (final (label, value) in metrics)
            AssenStatCard(value: formatThousands(value), label: label),
        ],
      ),
    );
  }
}

/// The loading state: a grid of stat-card-shaped skeletons.
class _StudioSkeleton extends StatelessWidget {
  const _StudioSkeleton();

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      child: AssenFeedGrid(
        minColumnWidth: 150,
        maxColumns: 2,
        columnSpacing: SpacingTokens.s3,
        rowSpacing: SpacingTokens.s3,
        children: List.generate(
          6,
          (_) => const AssenCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AssenSkeleton(width: 60),
                SizedBox(height: SpacingTokens.s2),
                AssenSkeleton(width: 80, height: 28),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
