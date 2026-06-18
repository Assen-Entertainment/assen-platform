import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/atoms/favorite_button.dart';
import 'package:ui_kit/src/layout/content_column.dart';
import 'package:ui_kit/src/layout/supporting_pane_scaffold.dart';
import 'package:ui_kit/src/layout/window_size.dart';
import 'package:ui_kit/src/molecules/collection_cell.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/bottom_cta.dart';
import 'package:ui_kit/src/organisms/schedule_calendar.dart';

/// The cast profile screen skeleton (`T3 캐스트 프로필`).
///
/// Covers the Templates/T3 row of `components.md` and the cast profile screen
/// (screens.md C3). It assembles an [AssenAppBar] with a back affordance, a
/// profile header ([AssenAvatar] + name + 최애 [AssenFavoriteButton]), the cast's
/// approved intro/event/cheki status, 출근 일정 ([AssenScheduleCalendar]), a 체키
/// 컬렉션 grid ([AssenCollectionCell]s over pastel motifs), and a pinned
/// [AssenBottomCta] (예약/최애 — Korean B2C convention #1: one bottom action).
/// The content scrolls under the bar.
///
/// Content is placeholder data (fictional cast 미오), surfaced as constructor
/// parameters so a real screen overrides it (screens.md mock rule).
class AssenCastProfileTemplate extends StatefulWidget {
  /// Creates the cast profile template.
  ///
  /// [castName]/[castHue]/[tagline] fill the header; [isFavorite] seeds the
  /// 최애 toggle. [schedule] is the cast's day strip. The `on*` callbacks are
  /// optional (the gallery passes no-ops).
  const AssenCastProfileTemplate({
    this.castName = '미오',
    this.castHue = AssenBadgeHue.strawberry,
    this.tagline = '딸기 담당 · 게임 마스터',
    this.introduction = '공식 동의된 소개만 표시하는 캐스트 프로필입니다.',
    this.eventSummary = '6월 콜라보 이벤트 참여',
    this.chekiAvailability = '체키 촬영 가능',
    this.isFavorite = false,
    this.schedule = _defaultSchedule,
    this.onBack,
    this.onReserve,
    this.onFavoriteChanged,
    super.key,
  });

  /// The cast member's name.
  final String castName;

  /// The cast identity hue (응원색).
  final AssenBadgeHue castHue;

  /// The cast catchphrase/role line.
  final String tagline;

  /// The approved public introduction shown on the profile.
  final String introduction;

  /// The upcoming event summary for this cast.
  final String eventSummary;

  /// Cheki availability display copy.
  final String chekiAvailability;

  /// Whether this cast starts as the viewer's 최애.
  final bool isFavorite;

  /// The cast's weekly 출근 strip.
  final List<AssenScheduleDay> schedule;

  /// Optional back handler.
  final VoidCallback? onBack;

  /// Optional reservation handler (the bottom CTA).
  final VoidCallback? onReserve;

  /// Optional handler for favorite registration changes.
  final ValueChanged<bool>? onFavoriteChanged;

  /// The unified placeholder 출근 strip for this cast.
  static const List<AssenScheduleDay> _defaultSchedule = [
    AssenScheduleDay(weekday: '월', day: 9),
    AssenScheduleDay(weekday: '화', day: 10, isClosed: true),
    AssenScheduleDay(
      weekday: '수',
      day: 11,
      hasEvent: true,
      casts: [
        AssenScheduleCast(
          name: '미오',
          shift: '12:00–18:00',
          hue: AssenBadgeHue.strawberry,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '목', day: 12),
    AssenScheduleDay(
      weekday: '금',
      day: 13,
      casts: [
        AssenScheduleCast(
          name: '미오',
          shift: '15:00–21:00',
          hue: AssenBadgeHue.strawberry,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '토', day: 14),
    AssenScheduleDay(weekday: '일', day: 15, isClosed: true),
  ];

  @override
  State<AssenCastProfileTemplate> createState() =>
      _AssenCastProfileTemplateState();
}

class _AssenCastProfileTemplateState extends State<AssenCastProfileTemplate> {
  late bool _favorite = widget.isFavorite;
  int _scheduleDay = 2;

  @override
  void didUpdateWidget(covariant AssenCastProfileTemplate oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isFavorite != widget.isFavorite) {
      _favorite = widget.isFavorite;
    }
  }

  void _setFavorite(bool value) {
    setState(() => _favorite = value);
    widget.onFavoriteChanged?.call(value);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: widget.castName,
        onBack: widget.onBack ?? () {},
      ),
      bottomNavigationBar: AssenBottomCta(
        primaryLabel: '예약하기',
        onPrimary: widget.onReserve ?? () {},
      ),
      // Compact/medium keep the single stacked column; at expanded and wider
      // the profile is a reading-centric detail page — width-capped and split
      // into a main (profile + 출근 일정) pane and a 체키 collection supporting
      // rail, so the chrome-less route fills the surface without full-bleed.
      body: LayoutBuilder(
        builder: (context, constraints) {
          final wide = AssenWindowSize.fromWidth(
            constraints.maxWidth,
          ).atLeast(AssenWindowSize.expanded);
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
                  children: wide
                      ? [_wideBody(colors)]
                      : _stackedChildren(colors),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  // Caps to the fan reading column (AssenContentColumn default) so the profile
  // text never goes full-bleed on a chrome-less wide route.
  Widget _wideBody(AssenColors colors) => AssenContentColumn(
    child: AssenSupportingPaneScaffold(
      main: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _header(),
          const SizedBox(height: SpacingTokens.s4),
          _summary(),
          const SizedBox(height: SpacingTokens.s6),
          const AssenSectionHeader(title: '출근 일정'),
          const SizedBox(height: SpacingTokens.s3),
          _calendar(),
        ],
      ),
      supporting: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AssenSectionHeader(
            title: '체키 컬렉션',
            actionLabel: '전체보기',
            onAction: () {},
          ),
          const SizedBox(height: SpacingTokens.s3),
          _ChekiGrid(colors: colors),
        ],
      ),
    ),
  );

  List<Widget> _stackedChildren(AssenColors colors) => [
    _header(),
    const SizedBox(height: SpacingTokens.s4),
    _summary(),
    const SizedBox(height: SpacingTokens.s6),
    const AssenSectionHeader(title: '출근 일정'),
    const SizedBox(height: SpacingTokens.s3),
    _calendar(),
    const SizedBox(height: SpacingTokens.s6),
    AssenSectionHeader(
      title: '체키 컬렉션',
      actionLabel: '전체보기',
      onAction: () {},
    ),
    const SizedBox(height: SpacingTokens.s3),
    _ChekiGrid(colors: colors),
  ];

  Widget _header() => _ProfileHeader(
    name: widget.castName,
    hue: widget.castHue,
    tagline: widget.tagline,
    isFavorite: _favorite,
    onFavoriteChanged: _setFavorite,
  );

  Widget _summary() => _ProfileSummary(
    introduction: widget.introduction,
    eventSummary: widget.eventSummary,
    chekiAvailability: widget.chekiAvailability,
  );

  Widget _calendar() => AssenScheduleCalendar(
    days: widget.schedule,
    selectedIndex: _scheduleDay,
    todayIndex: 2,
    onSelect: (i) => setState(() => _scheduleDay = i),
  );
}

/// The profile header: large avatar, name, catchphrase, and the 최애 toggle.
class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.name,
    required this.hue,
    required this.tagline,
    required this.isFavorite,
    required this.onFavoriteChanged,
  });

  final String name;
  final AssenBadgeHue hue;
  final String tagline;
  final bool isFavorite;
  final ValueChanged<bool> onFavoriteChanged;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Row(
      children: [
        AssenAvatar(name: name, hue: hue, size: AssenAvatarSize.l),
        const SizedBox(width: SpacingTokens.s4),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Row(
                children: [
                  AssenBadge(label: '출근중', hue: AssenBadgeHue.matcha),
                ],
              ),
              const SizedBox(height: SpacingTokens.s2),
              Text(
                name,
                style: TextStyle(
                  fontSize: TypographyTokens.headlineSize,
                  fontWeight: FontWeight.w800,
                  color: colors.ink900,
                ),
              ),
              const SizedBox(height: SpacingTokens.s1),
              Text(
                tagline,
                style: TextStyle(
                  fontSize: TypographyTokens.labelSize,
                  color: colors.ink700,
                ),
              ),
            ],
          ),
        ),
        AssenFavoriteButton(
          isFavorite: isFavorite,
          onChanged: onFavoriteChanged,
        ),
      ],
    );
  }
}

/// Approved public profile copy and capability badges.
class _ProfileSummary extends StatelessWidget {
  const _ProfileSummary({
    required this.introduction,
    required this.eventSummary,
    required this.chekiAvailability,
  });

  final String introduction;
  final String eventSummary;
  final String chekiAvailability;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: SpacingTokens.s2,
            runSpacing: SpacingTokens.s2,
            children: [
              const AssenBadge(label: '공식 프로필', hue: AssenBadgeHue.sky),
              AssenBadge(
                label: chekiAvailability,
              ),
              AssenBadge(label: eventSummary, hue: AssenBadgeHue.lavender),
            ],
          ),
          const SizedBox(height: SpacingTokens.s3),
          Text(
            introduction,
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              height: 1.45,
              color: colors.ink700,
            ),
          ),
          const SizedBox(height: SpacingTokens.s2),
          Text(
            '동의된 프로필 정보만 공개 중',
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              color: colors.ink500,
            ),
          ),
        ],
      ),
    );
  }
}

/// The 체키 컬렉션 grid — owned frames plus a locked/NEW placeholder.
class _ChekiGrid extends StatelessWidget {
  const _ChekiGrid({required this.colors});

  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    // A small fixed-content collection sample (owned · NEW · locked) — the
    // album proper lives in T4; here it previews this cast's frames.
    final cells = <Widget>[
      AssenCollectionCell(
        artwork: ColoredBox(color: colors.strawberryBg),
        label: '첫 방문 체키',
        onTap: () {},
      ),
      AssenCollectionCell(
        artwork: ColoredBox(color: colors.peachBg),
        label: '6월 콜라보',
        badge: const AssenBadge(label: 'NEW'),
        onTap: () {},
      ),
      const AssenCollectionCell(
        artwork: SizedBox.shrink(),
        label: '한정 체키',
        state: AssenCollectionState.locked,
      ),
    ];

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: SpacingTokens.s3,
        crossAxisSpacing: SpacingTokens.s3,
        // Square tile + a label line below it, so the cell is a touch taller.
        childAspectRatio: 0.82,
      ),
      itemCount: cells.length,
      itemBuilder: (context, index) => cells[index],
    );
  }
}
