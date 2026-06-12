import 'package:ui_kit/ui_kit.dart';

/// A mock member for the unified P3a scenario (체리체리 · HK-0042).
///
/// Placeholder identity + figures for the static app shell — NOT approved
/// values, internal design only (screens.md mock rule).
class FanMockMember {
  /// Creates a mock member.
  const FanMockMember({
    required this.name,
    required this.memberNumber,
    required this.points,
    required this.tierLabel,
    required this.stampsFilled,
    required this.stampSlots,
  });

  /// Display name on the membership card.
  final String name;

  /// Formatted membership number (e.g. "HK-0042").
  final String memberNumber;

  /// Loyalty point balance, pre-formatted.
  final String points;

  /// Tier label on the card strip.
  final String tierLabel;

  /// Filled visit-stamp cells.
  final int stampsFilled;

  /// Total stamp slots.
  final int stampSlots;
}

/// A mock cast member (fictional — 미오/유키/모카/베리, unrelated to real
/// candidates; screens.md mock rule).
class FanMockCast {
  /// Creates a mock cast entry.
  const FanMockCast({
    required this.id,
    required this.name,
    required this.hue,
    required this.tagline,
  });

  /// Stable id used in the `/cast/:id` deep link.
  final String id;

  /// Display name.
  final String name;

  /// Identity hue (응원색).
  final AssenBadgeHue hue;

  /// Catchphrase/role line.
  final String tagline;
}

/// The single source of fan-app mock data (체리체리 HK-0042 scenario).
///
/// Centralising it keeps screens free of scattered literals and matches the
/// templates' unified placeholder set. No design tokens here — colours come
/// from `ui_kit`/`core_tokens` at the widget (screens hard-code 0 tokens).
abstract final class FanMockData {
  /// The mock member.
  static const FanMockMember member = FanMockMember(
    name: '체리체리',
    memberNumber: 'HK-0042',
    points: '1,280',
    tierLabel: '하츠코이',
    stampsFilled: 5,
    stampSlots: 8,
  );

  /// The fictional cast roster, keyed for `/cast/:id` lookup.
  static const List<FanMockCast> casts = [
    FanMockCast(
      id: 'mio',
      name: '미오',
      hue: AssenBadgeHue.strawberry,
      tagline: '딸기 담당 · 게임 마스터',
    ),
    FanMockCast(
      id: 'yuki',
      name: '유키',
      hue: AssenBadgeHue.sky,
      tagline: '하늘빛 미소 · 노래 담당',
    ),
    FanMockCast(
      id: 'moka',
      name: '모카',
      hue: AssenBadgeHue.peach,
      tagline: '디저트 소믈리에',
    ),
    FanMockCast(
      id: 'berry',
      name: '베리',
      hue: AssenBadgeHue.lavender,
      tagline: '보드게임 길잡이',
    ),
  ];

  /// Resolves a cast by [id], falling back to the first (미오) for unknown ids
  /// so a stray deep link still renders a valid profile.
  static FanMockCast castById(String id) => casts.firstWhere(
    (c) => c.id == id,
    orElse: () => casts.first,
  );

  /// Today's index within [homeWeek] (오늘 6.11 = 수, first cell of the strip).
  static const int todayIndexHome = 0;

  /// The home preview week strip (오늘 + the rest of the week).
  static const List<AssenScheduleDay> homeWeek = [
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
}
