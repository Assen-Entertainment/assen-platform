import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/mock/fan_mock_data.dart';
import 'package:fan_app/router/routes.dart';
import 'package:fan_app/state/favorite_cast_store.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The home tab body (C0) — wires the home composition into the router shell.
///
/// Re-hosts the [AssenHomeTemplate] body (membership card, visit stamp board,
/// 오늘의 출근 preview, 최애 캐스트, event banner) as a thin screen so the bottom
/// tab bar belongs to the shell, not the template, and the card/section actions
/// route for real (회원증 QR → /qr, 캐스트 → /cast/:id, 출근표 → the schedule tab).
/// The template stays the visual blueprint; only the chrome and the no-op
/// callbacks differ. Mock data is the unified set (체리체리 HK-0042, fictional
/// cast) from [FanMockData] — no unapproved figures (screens.md mock rule).
class HomeScreen extends StatefulWidget {
  /// Creates the home tab body.
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedDay = FanMockData.todayIndexHome;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: '하츠코이',
        actions: [
          AssenIconButton(
            icon: Icons.notifications_none,
            semanticLabel: '알림',
            onPressed: () => context.go(FanRoutes.my),
          ),
        ],
      ),
      // The same sections lay out as one stacked reading column on
      // compact/medium widths and as a two-column dashboard on expanded
      // web/desktop widths, so a wide browser fills the surface with content
      // instead of leaving large empty gutters around a narrow column.
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isExpanded =
              AssenWindowSize.fromWidth(constraints.maxWidth) ==
              AssenWindowSize.expanded;
          return CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(
                  SpacingTokens.screenMargin,
                  SpacingTokens.s4,
                  SpacingTokens.screenMargin,
                  SpacingTokens.s8,
                ),
                sliver: SliverList.list(
                  children: isExpanded
                      ? _dashboardChildren(context)
                      : _stackedChildren(context),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  /// Stacked single-column layout for compact/medium widths (mobile/tablet).
  List<Widget> _stackedChildren(BuildContext context) => [
    _membershipCard(context),
    const SizedBox(height: SpacingTokens.s5),
    _stampCard(),
    const SizedBox(height: SpacingTokens.s6),
    _scheduleSection(context),
    const SizedBox(height: SpacingTokens.s6),
    _favoritesSection(context),
    const SizedBox(height: SpacingTokens.s6),
    _eventSection(context),
  ];

  /// Two-column dashboard for expanded widths: the membership card spans the
  /// full width, then the remaining sections pair up two-per-row.
  ///
  /// The layout is row-major (each [Row] holds the next two sections) rather
  /// than two independent columns, so the source order — stamps, schedule,
  /// favorites, events — matches the visual left-to-right, top-to-bottom
  /// reading order. That keeps screen-reader and focus traversal aligned with
  /// what's on screen instead of reading down one column and back up the other.
  List<Widget> _dashboardChildren(BuildContext context) => [
    _membershipCard(context),
    const SizedBox(height: SpacingTokens.s5),
    _dashboardRow(_stampCard(), _scheduleSection(context)),
    const SizedBox(height: SpacingTokens.s6),
    _dashboardRow(_favoritesSection(context), _eventSection(context)),
  ];

  Widget _dashboardRow(Widget left, Widget right) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(child: left),
      const SizedBox(width: SpacingTokens.s5),
      Expanded(child: right),
    ],
  );

  Widget _membershipCard(BuildContext context) {
    const member = FanMockData.member;
    return AssenMembershipCard(
      name: member.name,
      memberNumber: member.memberNumber,
      points: member.points,
      tierLabel: member.tierLabel,
      avatar: AssenAvatar(name: member.name, hue: AssenBadgeHue.strawberry),
      onShowQr: () => context.push(FanRoutes.qr),
    );
  }

  Widget _stampCard() {
    const member = FanMockData.member;
    return AssenStampCard(
      title: '방문 스탬프',
      filled: member.stampsFilled,
      slots: member.stampSlots,
      rewardLabel: '체키',
    );
  }

  Widget _scheduleSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AssenSectionHeader(
          title: '오늘의 출근',
          actionLabel: '출근표',
          onAction: () => context.go(FanRoutes.schedule),
        ),
        const SizedBox(height: SpacingTokens.s3),
        AssenScheduleCalendar(
          days: FanMockData.homeWeek,
          selectedIndex: _selectedDay,
          todayIndex: FanMockData.todayIndexHome,
          onSelect: (i) => setState(() => _selectedDay = i),
        ),
      ],
    );
  }

  Widget _favoritesSection(BuildContext context) {
    final favorites = FanFavoriteStore.instance;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AssenSectionHeader(
          title: '최애 캐스트',
          actionLabel: '전체보기',
          onAction: () => context.go(FanRoutes.schedule),
        ),
        const SizedBox(height: SpacingTokens.s3),
        ListenableBuilder(
          listenable: favorites,
          builder: (context, _) => _FavoriteCastPreview(
            favorites: favorites,
            onOpenSchedule: () => context.go(FanRoutes.schedule),
            onOpenCast: (castId) => context.push(FanRoutes.castPath(castId)),
          ),
        ),
      ],
    );
  }

  Widget _eventSection(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const AssenSectionHeader(title: '이벤트'),
        const SizedBox(height: SpacingTokens.s3),
        AssenBannerCard(
          title: '6월 콜라보 이벤트',
          subtitle: '6.10 – 6.30 · 한정 체키 증정',
          background: ColoredBox(color: colors.lavenderBg),
          onTap: () => context.push(FanRoutes.events),
        ),
      ],
    );
  }
}

class _FavoriteCastPreview extends StatelessWidget {
  const _FavoriteCastPreview({
    required this.favorites,
    required this.onOpenSchedule,
    required this.onOpenCast,
  });

  final FanFavoriteStore favorites;
  final VoidCallback onOpenSchedule;
  final ValueChanged<String> onOpenCast;

  @override
  Widget build(BuildContext context) {
    final favoriteCasts = FanMockData.casts
        .where((cast) => favorites.isFavorite(cast.id))
        .toList();

    if (favoriteCasts.isEmpty) {
      return AssenEmptyState(
        title: '아직 등록한 최애가 없어요',
        message: '캐스트 프로필에서 하트를 눌러\n출근표와 이벤트를 먼저 확인해요.',
        actionLabel: '출근표 보기',
        onAction: onOpenSchedule,
      );
    }

    return Column(
      children: [
        for (var i = 0; i < favoriteCasts.length; i++) ...[
          _FavoriteCastCard(
            cast: favoriteCasts[i],
            favorites: favorites,
            onTap: () => onOpenCast(favoriteCasts[i].id),
          ),
          if (i != favoriteCasts.length - 1)
            const SizedBox(height: SpacingTokens.s3),
        ],
      ],
    );
  }
}

class _FavoriteCastCard extends StatelessWidget {
  const _FavoriteCastCard({
    required this.cast,
    required this.favorites,
    required this.onTap,
  });

  final FanMockCast cast;
  final FanFavoriteStore favorites;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AssenCastProfileCard(
      name: cast.name,
      hue: cast.hue,
      tagline: cast.tagline,
      isOnShift: _isOnShiftToday(cast.name),
      isFavorite: favorites.isFavorite(cast.id),
      onFavoriteChanged: (isFavorite) => favorites.setFavorite(
        cast.id,
        isFavorite: isFavorite,
      ),
      onTap: onTap,
    );
  }

  bool _isOnShiftToday(String castName) =>
      FanMockData.homeWeek[FanMockData.todayIndexHome].casts.any(
        (cast) => cast.name == castName,
      );
}
