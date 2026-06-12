import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/favorite_button.dart';
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
/// 출근 일정 ([AssenScheduleCalendar]), a 체키 컬렉션 grid ([AssenCollectionCell]s
/// over pastel motifs), and a pinned [AssenBottomCta] (예약/최애 — Korean B2C
/// convention #1: one bottom action). The content scrolls under the bar.
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
    this.isFavorite = false,
    this.schedule = _defaultSchedule,
    this.onBack,
    this.onReserve,
    super.key,
  });

  /// The cast member's name.
  final String castName;

  /// The cast identity hue (응원색).
  final AssenBadgeHue castHue;

  /// The cast catchphrase/role line.
  final String tagline;

  /// Whether this cast starts as the viewer's 최애.
  final bool isFavorite;

  /// The cast's weekly 출근 strip.
  final List<AssenScheduleDay> schedule;

  /// Optional back handler.
  final VoidCallback? onBack;

  /// Optional reservation handler (the bottom CTA).
  final VoidCallback? onReserve;

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
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s4,
              SpacingTokens.screenMargin,
              SpacingTokens.s8,
            ),
            sliver: SliverList.list(
              children: [
                _ProfileHeader(
                  name: widget.castName,
                  hue: widget.castHue,
                  tagline: widget.tagline,
                  isFavorite: _favorite,
                  onFavoriteChanged: (v) => setState(() => _favorite = v),
                ),
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '출근 일정'),
                const SizedBox(height: SpacingTokens.s3),
                AssenScheduleCalendar(
                  days: widget.schedule,
                  selectedIndex: _scheduleDay,
                  todayIndex: 2,
                  onSelect: (i) => setState(() => _scheduleDay = i),
                ),
                const SizedBox(height: SpacingTokens.s6),
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
        ],
      ),
    );
  }
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
