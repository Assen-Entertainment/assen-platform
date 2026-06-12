import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:fan_app/state/favorite_cast_store.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The schedule tab body (C1 출근표) — re-hosts the [AssenScheduleTemplate]
/// body in the router shell so cast taps deep-link to `/cast/:id`.
///
/// The week strip, the 최애 filter chips and the working-cast list match the
/// template; the shell owns the bottom tab bar, and selecting a cast pushes
/// the profile route. Mock data is the unified fictional set (mock rule).
class ScheduleScreen extends StatefulWidget {
  /// Creates the schedule tab body.
  const ScheduleScreen({super.key});

  @override
  State<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends State<ScheduleScreen> {
  static const int _todayIndex = 2; // 오늘 6.11 = 수 (index 2)
  static const List<String> _filters = ['전체', '미오', '유키', '모카', '베리'];

  static const Map<String, AssenBadgeHue> _castHues = {
    '미오': AssenBadgeHue.strawberry,
    '유키': AssenBadgeHue.sky,
    '모카': AssenBadgeHue.peach,
    '베리': AssenBadgeHue.lavender,
  };

  static const Map<String, String> _castIds = {
    '미오': 'mio',
    '유키': 'yuki',
    '모카': 'moka',
    '베리': 'berry',
  };

  static const List<AssenScheduleDay> _week = [
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

  int _selectedDay = _todayIndex;
  int _filter = 0;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final favorites = FanFavoriteStore.instance;
    final casts = _week[_selectedDay].casts;
    final selectedFilter = _filters[_filter];
    final emptyMessage = casts.isEmpty
        ? '이 날은 예정된 출근이 없어요'
        : '$selectedFilter 출근 예정이 없어요';

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '출근표'),
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
                  labels: _filters,
                  selectedIndex: _filter,
                  onSelect: (i) => setState(() => _filter = i),
                ),
                const SizedBox(height: SpacingTokens.s5),
                AssenScheduleCalendar(
                  days: _week,
                  selectedIndex: _selectedDay,
                  todayIndex: _todayIndex,
                  onSelect: (i) => setState(() => _selectedDay = i),
                ),
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '출근 캐스트'),
                const SizedBox(height: SpacingTokens.s3),
                ListenableBuilder(
                  listenable: favorites,
                  builder: (context, _) {
                    final visibleCasts = _visibleCasts(casts, favorites);

                    if (visibleCasts.isEmpty) {
                      return _NoCastNotice(
                        message: emptyMessage,
                        colors: colors,
                      );
                    }

                    return Column(
                      children: [
                        for (final cast in visibleCasts) ...[
                          AssenCastProfileCard(
                            name: cast.name,
                            hue: _castHues[cast.name] ??
                                AssenBadgeHue.strawberry,
                            tagline: '출근 ${cast.shift}',
                            isOnShift: true,
                            isFavorite: favorites.isFavorite(
                              _castIdFor(cast.name),
                            ),
                            onFavoriteChanged: (isFavorite) {
                              favorites.setFavorite(
                                _castIdFor(cast.name),
                                isFavorite: isFavorite,
                              );
                            },
                            onTap: () => context.push(
                              FanRoutes.castPath(_castIdFor(cast.name)),
                            ),
                          ),
                          const SizedBox(height: SpacingTokens.s3),
                        ],
                      ],
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<AssenScheduleCast> _visibleCasts(
    List<AssenScheduleCast> casts,
    FanFavoriteStore favorites,
  ) {
    final selectedFilter = _filters[_filter];
    final filtered = _filter == 0
        ? [...casts]
        : casts.where((cast) => cast.name == selectedFilter).toList();

    if (_filter != 0) return filtered;

    filtered.sort((a, b) {
      final aFavorite = favorites.isFavorite(_castIdFor(a.name));
      final bFavorite = favorites.isFavorite(_castIdFor(b.name));
      if (aFavorite == bFavorite) return 0;
      return aFavorite ? -1 : 1;
    });
    return filtered;
  }

  String _castIdFor(String castName) => _castIds[castName] ?? 'mio';
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
  const _NoCastNotice({required this.message, required this.colors});

  final String message;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s8),
      alignment: Alignment.center,
      child: Text(
        message,
        style: TextStyle(
          fontSize: TypographyTokens.bodyMSize,
          fontWeight: FontWeight.w600,
          color: colors.ink500,
        ),
      ),
    );
  }
}
