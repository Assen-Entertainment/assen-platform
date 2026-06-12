import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';

/// A single day in the [AssenScheduleCalendar] weekly strip.
///
/// [hasEvent] adds the event dot; [isClosed] marks a 휴무 (rest) day; [casts] are
/// the working cast members shown when this day is selected.
class AssenScheduleDay {
  /// Creates a schedule day.
  const AssenScheduleDay({
    required this.weekday,
    required this.day,
    this.hasEvent = false,
    this.isClosed = false,
    this.casts = const [],
  });

  /// The weekday label (e.g. "월").
  final String weekday;

  /// The day-of-month number.
  final int day;

  /// Whether an event is scheduled (adds the event dot).
  final bool hasEvent;

  /// Whether the café is closed that day (휴무).
  final bool isClosed;

  /// The cast members working that day (shown when the day is selected).
  final List<AssenScheduleCast> casts;
}

/// A working cast slot in a [AssenScheduleDay] (name + identity hue + shift).
class AssenScheduleCast {
  /// Creates a cast schedule slot.
  const AssenScheduleCast({
    required this.name,
    required this.shift,
    this.hue,
  });

  /// The cast member's name.
  final String name;

  /// The shift window (e.g. "12:00–18:00").
  final String shift;

  /// The cast identity hue for the avatar ring (응원색, references #11).
  final AssenBadgeHue? hue;
}

/// The weekly schedule board (`주간 출근표 — 이벤트점/선택/오늘/휴무`).
///
/// Covers the Domain/ScheduleCalendar row of `components.md` and the 출근표 screen
/// (screens.md C1). A horizontal week strip of [days] (each a date pill marking
/// today, the selected day, an event dot, or a 휴무) over the working-cast list
/// for the [selectedIndex] day. Selection is driven by [onSelect]; the selected
/// pill uses the rose action anchor, today is outlined, closed days are muted
/// (never darkened — disabled is muted, tokens.md §1). Cast rows compose
/// [AssenAvatar] with the cast's identity hue.
class AssenScheduleCalendar extends StatelessWidget {
  /// Creates a weekly schedule for [days].
  ///
  /// [selectedIndex] is the focused day (its casts are listed); [todayIndex]
  /// marks today's pill. [onSelect] reports day taps.
  const AssenScheduleCalendar({
    required this.days,
    required this.selectedIndex,
    required this.onSelect,
    this.todayIndex,
    super.key,
  }) : assert(days.length > 0, 'A schedule needs at least one day');

  /// The week's days.
  final List<AssenScheduleDay> days;

  /// The selected day index (its cast list is shown).
  final int selectedIndex;

  /// The index of today's pill, or null if today is outside the week.
  final int? todayIndex;

  /// Reports a tapped day index.
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final selected = days[selectedIndex];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            for (var i = 0; i < days.length; i++)
              Expanded(
                child: _DayPill(
                  day: days[i],
                  isSelected: i == selectedIndex,
                  isToday: i == todayIndex,
                  colors: colors,
                  onTap: () => onSelect(i),
                ),
              ),
          ],
        ),
        const SizedBox(height: SpacingTokens.s5),
        if (selected.isClosed)
          _ClosedRow(colors: colors)
        else if (selected.casts.isEmpty)
          _ClosedRow(colors: colors, label: '예정된 출근이 없어요')
        else
          for (final cast in selected.casts) ...[
            _CastRow(cast: cast, colors: colors),
            const SizedBox(height: SpacingTokens.s3),
          ],
      ],
    );
  }
}

/// A single date pill in the week strip.
class _DayPill extends StatelessWidget {
  const _DayPill({
    required this.day,
    required this.isSelected,
    required this.isToday,
    required this.colors,
    required this.onTap,
  });

  final AssenScheduleDay day;
  final bool isSelected;
  final bool isToday;
  final AssenColors colors;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color background;
    final Color dayInk;
    if (isSelected) {
      background = colors.roseMain;
      dayInk = colors.white;
    } else {
      background = Colors.transparent;
      dayInk = day.isClosed ? colors.ink300 : colors.ink900;
    }

    return Semantics(
      button: true,
      selected: isSelected,
      label:
          '${day.weekday} ${day.day}일'
          '${isToday ? ', 오늘' : ''}${day.isClosed ? ', 휴무' : ''}',
      child: InkWell(
        onTap: onTap,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        child: Container(
          constraints: const BoxConstraints(minHeight: 64),
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
          decoration: BoxDecoration(
            color: background,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.md),
            ),
            border: isToday && !isSelected
                ? Border.all(color: colors.roseMain)
                : null,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                day.weekday,
                style: TextStyle(
                  fontSize: TypographyTokens.captionMicroSize,
                  fontWeight: FontWeight.w700,
                  color: isSelected ? colors.white : colors.ink500,
                ),
              ),
              const SizedBox(height: SpacingTokens.s1),
              Text(
                '${day.day}',
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: dayInk,
                ),
              ),
              const SizedBox(height: SpacingTokens.s1),
              // Event dot — present days with an event, hollow placeholder else
              // so the baseline never shifts between dotted/undotted pills.
              Container(
                width: SpacingTokens.s1,
                height: SpacingTokens.s1,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: day.hasEvent
                      ? (isSelected ? colors.white : colors.strawberryInk)
                      : Colors.transparent,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A working-cast row: avatar + name + shift window.
class _CastRow extends StatelessWidget {
  const _CastRow({required this.cast, required this.colors});

  final AssenScheduleCast cast;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        AssenAvatar(name: cast.name, hue: cast.hue, isOnline: true),
        const SizedBox(width: SpacingTokens.s3),
        Expanded(
          child: Text(
            cast.name,
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              fontWeight: FontWeight.w700,
              color: colors.ink900,
            ),
          ),
        ),
        Text(
          cast.shift,
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            fontWeight: FontWeight.w600,
            color: colors.ink700,
          ),
        ),
      ],
    );
  }
}

/// The muted row shown for a closed (휴무) or empty schedule day.
class _ClosedRow extends StatelessWidget {
  const _ClosedRow({required this.colors, this.label = '휴무일이에요'});

  final AssenColors colors;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s5),
      alignment: Alignment.center,
      child: Text(
        label,
        style: TextStyle(
          fontSize: TypographyTokens.bodySSize,
          fontWeight: FontWeight.w600,
          color: colors.ink500,
        ),
      ),
    );
  }
}
