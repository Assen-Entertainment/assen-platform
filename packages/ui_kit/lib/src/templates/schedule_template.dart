import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/chips.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/cast_profile_card.dart';
import 'package:ui_kit/src/organisms/schedule_calendar.dart';

/// The weekly schedule screen skeleton (`T2 출근표`).
///
/// Covers the Templates/T2 row of `components.md` and the 출근표 screen
/// (screens.md C1). It assembles an [AssenAppBar], a 최애 filter row of
/// [AssenFilterChip]s, the weekly [AssenScheduleCalendar], the working-cast
/// slot list as [AssenCastProfileCard]s for the selected day, and the
/// [AssenTabBar] with 출근표 active. The body scrolls (a [CustomScrollView]).
///
/// Content is placeholder data (fictional cast 미오/유키/모카/베리), surfaced as
/// constructor parameters so a real screen overrides them (screens.md mock
/// rule). Selecting a day or a filter is handled internally for the gallery.
class AssenScheduleTemplate extends StatefulWidget {
  /// Creates the schedule template.
  ///
  /// [week] is the day strip; [todayIndex] marks today and seeds the initial
  /// selection. [filters] are the 최애 filter labels. The `on*` callbacks are
  /// optional (the gallery passes no-ops).
  const AssenScheduleTemplate({
    this.week = _defaultWeek,
    this.todayIndex = 2,
    this.filters = const ['전체', '미오', '유키', '모카', '베리'],
    this.onBack,
    super.key,
  });

  /// The week's day strip.
  final List<AssenScheduleDay> week;

  /// The index of today's pill (also the initial selection).
  final int todayIndex;

  /// The 최애 filter labels (the first is the "전체" reset).
  final List<String> filters;

  /// Optional back handler (omit on a tab root).
  final VoidCallback? onBack;

  /// The unified placeholder week (오늘 6.11 = index 2 — 수요일).
  static const List<AssenScheduleDay> _defaultWeek = [
    AssenScheduleDay(
      weekday: '월',
      day: 9,
      casts: [
        AssenScheduleCast(
          name: '미오',
          shift: '12:00–18:00',
          hue: AssenBadgeHue.strawberry,
        ),
      ],
    ),
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
    AssenScheduleDay(
      weekday: '목',
      day: 12,
      casts: [
        AssenScheduleCast(
          name: '베리',
          shift: '12:00–18:00',
          hue: AssenBadgeHue.lavender,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '금', day: 13, hasEvent: true),
    AssenScheduleDay(weekday: '토', day: 14),
    AssenScheduleDay(weekday: '일', day: 15, isClosed: true),
  ];

  @override
  State<AssenScheduleTemplate> createState() => _AssenScheduleTemplateState();
}

class _AssenScheduleTemplateState extends State<AssenScheduleTemplate> {
  late int _selectedDay = widget.todayIndex;
  int _filter = 0;
  int _tab = 1;

  /// The cast hue assigned to a fictional cast name (응원색, references #11).
  static const Map<String, AssenBadgeHue> _castHues = {
    '미오': AssenBadgeHue.strawberry,
    '유키': AssenBadgeHue.sky,
    '모카': AssenBadgeHue.peach,
    '베리': AssenBadgeHue.lavender,
  };

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final casts = widget.week[_selectedDay].casts;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '출근표', onBack: widget.onBack),
      bottomNavigationBar: AssenTabBar(
        currentIndex: _tab,
        onChanged: (i) => setState(() => _tab = i),
        items: const [
          AssenTabItem(icon: Icons.home_outlined, label: '홈'),
          AssenTabItem(
            icon: Icons.calendar_month_outlined,
            activeIcon: Icons.calendar_month,
            label: '출근표',
          ),
          AssenTabItem(icon: Icons.event_outlined, label: '예약'),
          AssenTabItem(
            icon: Icons.photo_library_outlined,
            label: '체키',
            badgeCount: 3,
          ),
          AssenTabItem(icon: Icons.person_outline, label: '마이'),
        ],
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
                _FavoriteFilters(
                  labels: widget.filters,
                  selectedIndex: _filter,
                  onSelect: (i) => setState(() => _filter = i),
                ),
                const SizedBox(height: SpacingTokens.s5),
                AssenScheduleCalendar(
                  days: widget.week,
                  selectedIndex: _selectedDay,
                  todayIndex: widget.todayIndex,
                  onSelect: (i) => setState(() => _selectedDay = i),
                ),
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '출근 캐스트'),
                const SizedBox(height: SpacingTokens.s3),
                if (casts.isEmpty)
                  _NoCastNotice(colors: colors)
                else
                  for (final cast in casts) ...[
                    AssenCastProfileCard(
                      name: cast.name,
                      hue: _castHues[cast.name] ?? AssenBadgeHue.strawberry,
                      tagline: '출근 ${cast.shift}',
                      isOnShift: true,
                      isFavorite: cast.name == '미오',
                      onFavoriteChanged: (_) {},
                      onTap: () {},
                    ),
                    const SizedBox(height: SpacingTokens.s3),
                  ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The horizontally scrolling 최애 filter chip row.
class _FavoriteFilters extends StatelessWidget {
  const _FavoriteFilters({
    required this.labels,
    required this.selectedIndex,
    required this.onSelect,
  });

  final List<String> labels;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (var i = 0; i < labels.length; i++) ...[
            AssenFilterChip(
              label: labels[i],
              selected: i == selectedIndex,
              onSelected: (_) => onSelect(i),
            ),
            if (i != labels.length - 1) const SizedBox(width: SpacingTokens.s2),
          ],
        ],
      ),
    );
  }
}

/// The muted notice shown when the selected day has no scheduled cast.
class _NoCastNotice extends StatelessWidget {
  const _NoCastNotice({required this.colors});

  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s8),
      alignment: Alignment.center,
      child: Text(
        '이 날은 예정된 출근이 없어요',
        style: TextStyle(
          fontSize: TypographyTokens.bodyMSize,
          fontWeight: FontWeight.w600,
          color: colors.ink500,
        ),
      ),
    );
  }
}
