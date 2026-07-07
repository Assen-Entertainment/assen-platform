/// Shared relative-time formatting for the read surfaces (notifications, feed,
/// post detail, comments).
///
/// Extracted from the R8 notifications screen so the browsing screens (feed,
/// post, comments) render "when" identically rather than each re-deriving the
/// buckets. A local formatter — the app has no `intl` dependency — so a time
/// always renders as a Korean relative label (or a `YYYY.MM.DD` date past a
/// week) instead of a raw timestamp.
library;

/// Formats [time] relative to [now] (방금 전 / N분 전 / N시간 전 / N일 전 / 날짜).
///
/// Buckets: under a minute → `방금 전`, under an hour → `N분 전`, under a day →
/// `N시간 전`, under a week → `N일 전`, otherwise the absolute `YYYY.MM.DD` date.
/// A [time] in the future (clock skew) collapses to `방금 전` rather than a
/// negative count.
String relativeTime(DateTime time, DateTime now) {
  final diff = now.difference(time);
  if (diff.inMinutes < 1) return '방금 전';
  if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
  if (diff.inHours < 24) return '${diff.inHours}시간 전';
  if (diff.inDays < 7) return '${diff.inDays}일 전';
  return '${time.year}.${_two(time.month)}.${_two(time.day)}';
}

/// Zero-pads a month/day to two digits.
String _two(int value) => value.toString().padLeft(2, '0');
