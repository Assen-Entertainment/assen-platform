import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/molecules/banner_card.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/cast_profile_card.dart';
import 'package:ui_kit/src/organisms/membership_card.dart';
import 'package:ui_kit/src/organisms/schedule_calendar.dart';
import 'package:ui_kit/src/organisms/stamp_card.dart';

/// The home screen skeleton (`T1 홈(회원증)`).
///
/// Covers the Templates/T1 row of `components.md` and the home screen
/// (screens.md C0). It assembles the signature surfaces into the first tab:
/// an [AssenAppBar], the [AssenMembershipCard] hero, the visit
/// [AssenStampCard], a 오늘의 출근 preview (a [AssenScheduleCalendar] focused on
/// today plus a [AssenCastProfileCard] row), an event [AssenBannerCard], and
/// the [AssenTabBar] with 홈 active. The body scrolls (a [CustomScrollView]);
/// the tab bar is the screen chrome (Korean B2C convention — bottom 5-tab nav).
///
/// Content is placeholder data (the unified mock — 체리체리 HK-0042, fictional
/// cast 미오/유키/모카/베리), surfaced as constructor parameters so a real
/// screen overrides them. No unapproved figures are shown (screens.md mock
/// rule; Development_Constraints — internal design only).
class AssenHomeTemplate extends StatefulWidget {
  /// Creates the home template.
  ///
  /// [memberName]/[memberNumber]/[points]/[tierLabel] fill the membership card.
  /// [stampsFilled]/[stampSlots] drive the stamp board. [todaySchedule] is the
  /// week strip used for the 오늘의 출근 preview, focused on [todayIndex]. The
  /// `on*` callbacks are optional (the gallery passes no-ops).
  const AssenHomeTemplate({
    this.memberName = '체리체리',
    this.memberNumber = 'HK-0042',
    this.points = '1,280',
    this.tierLabel = '하츠코이',
    this.stampsFilled = 5,
    this.stampSlots = 8,
    this.todaySchedule = _defaultWeek,
    this.todayIndex = 0,
    this.onShowQr,
    this.onNotifications,
    super.key,
  });

  /// The member's display name shown on the card.
  final String memberName;

  /// The formatted membership number (e.g. "HK-0042").
  final String memberNumber;

  /// The loyalty point balance, pre-formatted.
  final String points;

  /// The tier name on the card strip (e.g. "하츠코이").
  final String tierLabel;

  /// Number of stamped visit cells.
  final int stampsFilled;

  /// Total stamp slots on the board.
  final int stampSlots;

  /// The day strip backing the 오늘의 출근 preview.
  final List<AssenScheduleDay> todaySchedule;

  /// The focused day index within [todaySchedule] (today).
  final int todayIndex;

  /// Opens the full QR membership; null hides the card's QR button.
  final VoidCallback? onShowQr;

  /// Opens notifications from the app bar.
  final VoidCallback? onNotifications;

  /// The unified placeholder week — today (오늘 6.11) plus the rest of the week.
  static const List<AssenScheduleDay> _defaultWeek = [
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
        AssenScheduleCast(
          name: '유키',
          shift: '13:00–19:00',
          hue: AssenBadgeHue.sky,
        ),
        AssenScheduleCast(
          name: '모카',
          shift: '16:00–22:00',
          hue: AssenBadgeHue.peach,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '목', day: 12),
    AssenScheduleDay(weekday: '금', day: 13, hasEvent: true),
    AssenScheduleDay(weekday: '토', day: 14),
    AssenScheduleDay(weekday: '일', day: 15, isClosed: true),
  ];

  @override
  State<AssenHomeTemplate> createState() => _AssenHomeTemplateState();
}

class _AssenHomeTemplateState extends State<AssenHomeTemplate> {
  late int _selectedDay = widget.todayIndex;
  int _tab = 0;

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
            onPressed: widget.onNotifications ?? () {},
          ),
        ],
      ),
      bottomNavigationBar: _HomeTabBar(
        currentIndex: _tab,
        onChanged: (i) => setState(() => _tab = i),
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
                AssenMembershipCard(
                  name: widget.memberName,
                  memberNumber: widget.memberNumber,
                  points: widget.points,
                  tierLabel: widget.tierLabel,
                  avatar: AssenAvatar(
                    name: widget.memberName,
                    hue: AssenBadgeHue.strawberry,
                  ),
                  onShowQr: widget.onShowQr ?? () {},
                ),
                const SizedBox(height: SpacingTokens.s5),
                AssenStampCard(
                  title: '방문 스탬프',
                  filled: widget.stampsFilled,
                  slots: widget.stampSlots,
                  rewardLabel: '체키',
                ),
                const SizedBox(height: SpacingTokens.s6),
                AssenSectionHeader(
                  title: '오늘의 출근',
                  actionLabel: '출근표',
                  onAction: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                AssenScheduleCalendar(
                  days: widget.todaySchedule,
                  selectedIndex: _selectedDay,
                  todayIndex: widget.todayIndex,
                  onSelect: (i) => setState(() => _selectedDay = i),
                ),
                const SizedBox(height: SpacingTokens.s6),
                AssenSectionHeader(
                  title: '최애 캐스트',
                  actionLabel: '전체보기',
                  onAction: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                AssenCastProfileCard(
                  name: '미오',
                  hue: AssenBadgeHue.strawberry,
                  tagline: '오늘도 잘 부탁해요',
                  isOnShift: true,
                  isFavorite: true,
                  onFavoriteChanged: (_) {},
                  onTap: () {},
                ),
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '이벤트'),
                const SizedBox(height: SpacingTokens.s3),
                AssenBannerCard(
                  title: '6월 콜라보 이벤트',
                  subtitle: '6.10 – 6.30 · 한정 체키 증정',
                  background: ColoredBox(color: colors.lavenderBg),
                  onTap: () {},
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The fan-app bottom tab bar with 홈 active (shared chrome across templates).
class _HomeTabBar extends StatelessWidget {
  const _HomeTabBar({required this.currentIndex, required this.onChanged});

  final int currentIndex;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return AssenTabBar(
      currentIndex: currentIndex,
      onChanged: onChanged,
      items: const [
        AssenTabItem(
          icon: Icons.home_outlined,
          activeIcon: Icons.home,
          label: '홈',
        ),
        AssenTabItem(icon: Icons.calendar_month_outlined, label: '출근표'),
        AssenTabItem(icon: Icons.event_outlined, label: '예약'),
        AssenTabItem(
          icon: Icons.photo_library_outlined,
          label: '체키',
          badgeCount: 3,
        ),
        AssenTabItem(icon: Icons.person_outline, label: '마이'),
      ],
    );
  }
}
