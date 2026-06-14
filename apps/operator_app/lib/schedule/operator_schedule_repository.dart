import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show TimeOfDay;

/// Publication lifecycle of a schedule entry (mirrors server `ScheduleStatus`).
///
/// 비공개 = [unpublished]; an entry is never deleted, only hidden from fans.
enum ScheduleEntryStatus {
  /// 초안 — draft, editable directly and not visible to fans.
  draft,

  /// 게시됨 — published, visible to fans; changes need an approval.
  published,

  /// 비공개 — unpublished, hidden from fans but preserved.
  unpublished,
}

/// The Korean label for a [ScheduleEntryStatus].
extension ScheduleEntryStatusLabel on ScheduleEntryStatus {
  /// The human-readable status label.
  String get label => switch (this) {
    ScheduleEntryStatus.draft => '초안',
    ScheduleEntryStatus.published => '게시됨',
    ScheduleEntryStatus.unpublished => '비공개',
  };
}

/// Lifecycle of a proposed change to a published entry (mirrors server
/// `ChangeRequestStatus`).
enum ScheduleChangeStatus {
  /// 승인 대기 — pending a different operator's decision.
  pending,

  /// 승인됨 — approved and applied to the entry.
  approved,

  /// 거부됨 — rejected without touching the entry.
  rejected,
}

/// The Korean label for a [ScheduleChangeStatus].
extension ScheduleChangeStatusLabel on ScheduleChangeStatus {
  /// The human-readable change-status label.
  String get label => switch (this) {
    ScheduleChangeStatus.pending => '승인 대기',
    ScheduleChangeStatus.approved => '승인됨',
    ScheduleChangeStatus.rejected => '거부됨',
  };
}

/// The mutable fields a change request may override (mirrors the server's
/// `_CHANGEABLE_FIELDS`).
///
/// Keys are the server's snake_case field names so the proposed/before maps are
/// a 1:1 mirror of the `ScheduleChangeRequest.proposed` JSON shape.
const List<String> kChangeableFields = <String>[
  'work_date',
  'start_time',
  'end_time',
  'note',
];

/// The Korean label for a changeable field key (for the before→after view).
String changeableFieldLabel(String key) => switch (key) {
  'work_date' => '근무일',
  'start_time' => '시작',
  'end_time' => '종료',
  'note' => '메모',
  _ => key,
};

/// One cast's work window on a date, as the operator console sees it.
///
/// Holds every status (the operator endpoint returns all of them, unlike the
/// fan read path). [startTime]/[endTime] are wall-clock windows; the
/// before/after snapshots serialise them as the server does (ISO strings).
@immutable
class OperatorScheduleEntry {
  /// Creates an immutable schedule entry row.
  const OperatorScheduleEntry({
    required this.id,
    required this.workDate,
    required this.castId,
    required this.startTime,
    required this.endTime,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.note = '',
  });

  /// Stable entry identifier.
  final String id;

  /// The work date (date-only; the time-of-day lives in [startTime]).
  final DateTime workDate;

  /// The cast identifier — a plain string (the cast app is a P0 placeholder).
  final String castId;

  /// Shift start (wall-clock).
  final TimeOfDay startTime;

  /// Shift end (wall-clock).
  final TimeOfDay endTime;

  /// Publication status.
  final ScheduleEntryStatus status;

  /// Optional operator note.
  final String note;

  /// When the entry was created.
  final DateTime createdAt;

  /// When the entry was last updated.
  final DateTime updatedAt;

  /// Returns a copy with selected fields replaced.
  OperatorScheduleEntry copyWith({
    DateTime? workDate,
    TimeOfDay? startTime,
    TimeOfDay? endTime,
    ScheduleEntryStatus? status,
    String? note,
    DateTime? updatedAt,
  }) {
    return OperatorScheduleEntry(
      id: id,
      workDate: workDate ?? this.workDate,
      castId: castId,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      status: status ?? this.status,
      note: note ?? this.note,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  /// The server-shaped snapshot of the mutable fields (for before/after).
  Map<String, String> snapshot() => <String, String>{
    'work_date': formatScheduleDate(workDate),
    'start_time': formatScheduleTime(startTime),
    'end_time': formatScheduleTime(endTime),
    'note': note,
  };
}

/// A proposed change to a published entry, pending approval — itself the change
/// log row (who requested/decided, when, before→after, reason).
///
/// Mirrors server `ScheduleChangeRequest`. [requestedById]/[decidedById] are the
/// operator account ids; the separation-of-duties guard compares them.
@immutable
class OperatorScheduleChangeRequest {
  /// Creates an immutable change-request row.
  const OperatorScheduleChangeRequest({
    required this.id,
    required this.entryId,
    required this.proposed,
    required this.before,
    required this.status,
    required this.requestedById,
    required this.createdAt,
    this.reason = '',
    this.decidedById,
    this.decisionNote = '',
  });

  /// Stable change-request identifier.
  final String id;

  /// The entry this change targets (the cast label is derived from the loaded
  /// entry — the server `ChangeRequestOut` returns only `entry_id`).
  final String entryId;

  /// Proposed field overrides (server-shaped: snake_case key → string value).
  final Map<String, String> proposed;

  /// Snapshot of the entry before the change (for the before→after view).
  final Map<String, String> before;

  /// Why the change was requested.
  final String reason;

  /// Decision lifecycle.
  final ScheduleChangeStatus status;

  /// The operator account id that filed the change.
  final int requestedById;

  /// The operator account id that decided it (null while pending).
  final int? decidedById;

  /// The approver/rejecter's decision note.
  final String decisionNote;

  /// When the change was filed.
  final DateTime createdAt;

  /// Returns a copy with the decision fields replaced.
  OperatorScheduleChangeRequest copyWith({
    ScheduleChangeStatus? status,
    int? decidedById,
    String? decisionNote,
  }) {
    return OperatorScheduleChangeRequest(
      id: id,
      entryId: entryId,
      proposed: proposed,
      before: before,
      reason: reason,
      status: status ?? this.status,
      requestedById: requestedById,
      decidedById: decidedById ?? this.decidedById,
      decisionNote: decisionNote ?? this.decisionNote,
      createdAt: createdAt,
    );
  }
}

/// Adapter boundary for operator schedule data (the API client lands later,
/// behind this same surface — mirroring the ASS-93 server contract).
abstract class OperatorScheduleRepository {
  /// Lists schedule entries (operator sees every status).
  List<OperatorScheduleEntry> listEntries();

  /// Lists change requests (the change log), optionally filtered by [status].
  ///
  /// The [status] parameter is typed as the enum, so an out-of-range filter is
  /// unrepresentable — the UI mirror of the server rejecting an unknown status
  /// with 400.
  List<OperatorScheduleChangeRequest> listChanges({
    ScheduleChangeStatus? status,
  });

  /// Creates a draft entry (not visible to fans until published).
  OperatorScheduleEntry createDraft({
    required DateTime workDate,
    required String castId,
    required TimeOfDay startTime,
    required TimeOfDay endTime,
    String note,
  });

  /// Edits a draft entry directly.
  ///
  /// Throws [StateError] when the entry is not a draft — published entries must
  /// go through [requestChange] (mirrors the server's `edit_draft` guard).
  OperatorScheduleEntry editDraft({
    required String entryId,
    TimeOfDay? startTime,
    TimeOfDay? endTime,
    String? note,
  });

  /// Publishes a draft/unpublished entry so fans can see it.
  OperatorScheduleEntry publishEntry(String entryId);

  /// Hides an entry from fans (비공개) without deleting it.
  OperatorScheduleEntry unpublishEntry({
    required String entryId,
    String reason,
  });

  /// Files a pending change to a published entry, stamped with [requestedById]
  /// (the current operator) so the separation-of-duties check at approval has a
  /// truthful requester — never a fixed placeholder.
  ///
  /// Throws [StateError] when the entry is not published (mirrors the server's
  /// `request_change` guard).
  OperatorScheduleChangeRequest requestChange({
    required String entryId,
    required Map<String, String> proposed,
    required int requestedById,
    String reason,
  });

  /// Approves a pending change and applies it to its entry.
  ///
  /// Throws [StateError] when [actorId] equals the requester (separation of
  /// duties) or the change is not pending — the same guards the server enforces
  /// authoritatively, mirrored here so a bypassed UI affordance still fails
  /// closed rather than silently applying a self-approval.
  OperatorScheduleChangeRequest approveChange({
    required String changeId,
    required int actorId,
    String decisionNote,
  });

  /// Rejects a pending change without touching its entry.
  ///
  /// Throws [StateError] when the change is not pending.
  OperatorScheduleChangeRequest rejectChange({
    required String changeId,
    required int actorId,
    String decisionNote,
  });
}

/// In-memory implementation used until the API client adapter lands.
class InMemoryOperatorScheduleRepository implements OperatorScheduleRepository {
  /// Creates the mock repository with deterministic rows.
  ///
  /// [now] anchors the seeded dates/timestamps so widget tests are stable.
  InMemoryOperatorScheduleRepository({DateTime? now})
    : _now = now ?? DateTime.now() {
    final today = DateTime(_now.year, _now.month, _now.day);
    final tomorrow = today.add(const Duration(days: 1));
    _entries.addAll([
      OperatorScheduleEntry(
        id: 'entry-1',
        workDate: today,
        castId: '미오',
        startTime: const TimeOfDay(hour: 12, minute: 0),
        endTime: const TimeOfDay(hour: 18, minute: 0),
        status: ScheduleEntryStatus.published,
        note: '오프닝 담당',
        createdAt: _now.subtract(const Duration(days: 2)),
        updatedAt: _now.subtract(const Duration(days: 1)),
      ),
      OperatorScheduleEntry(
        id: 'entry-2',
        workDate: today,
        castId: '유키',
        startTime: const TimeOfDay(hour: 13, minute: 0),
        endTime: const TimeOfDay(hour: 19, minute: 0),
        status: ScheduleEntryStatus.draft,
        createdAt: _now.subtract(const Duration(hours: 5)),
        updatedAt: _now.subtract(const Duration(hours: 5)),
      ),
      OperatorScheduleEntry(
        id: 'entry-3',
        workDate: tomorrow,
        castId: '모카',
        startTime: const TimeOfDay(hour: 16, minute: 0),
        endTime: const TimeOfDay(hour: 22, minute: 0),
        status: ScheduleEntryStatus.published,
        note: '이벤트 데이',
        createdAt: _now.subtract(const Duration(days: 1)),
        updatedAt: _now.subtract(const Duration(days: 1)),
      ),
      OperatorScheduleEntry(
        id: 'entry-4',
        workDate: tomorrow,
        castId: '베리',
        startTime: const TimeOfDay(hour: 12, minute: 0),
        endTime: const TimeOfDay(hour: 18, minute: 0),
        status: ScheduleEntryStatus.unpublished,
        createdAt: _now.subtract(const Duration(days: 1)),
        updatedAt: _now.subtract(const Duration(hours: 8)),
      ),
    ]);
    _changes.addAll([
      // Filed by operator #2, so operator #1 (the default viewer) may approve.
      OperatorScheduleChangeRequest(
        id: 'change-1',
        entryId: 'entry-1',
        proposed: const {'start_time': '13:00:00', 'end_time': '19:00:00'},
        before: const {'start_time': '12:00:00', 'end_time': '18:00:00'},
        reason: '오픈 시간 조정',
        status: ScheduleChangeStatus.pending,
        requestedById: 2,
        createdAt: _now.subtract(const Duration(hours: 3)),
      ),
      // Filed by operator #1 (the default viewer) — self-approval is blocked.
      OperatorScheduleChangeRequest(
        id: 'change-2',
        entryId: 'entry-3',
        proposed: const {'note': '이벤트 데이 (연장)'},
        before: const {'note': '이벤트 데이'},
        reason: '메모 보강',
        status: ScheduleChangeStatus.pending,
        requestedById: 1,
        createdAt: _now.subtract(const Duration(hours: 2)),
      ),
      // A decided change kept for the change-log history.
      OperatorScheduleChangeRequest(
        id: 'change-3',
        entryId: 'entry-1',
        proposed: const {'note': '오프닝 담당'},
        before: const {'note': ''},
        reason: '담당 메모 추가',
        status: ScheduleChangeStatus.approved,
        requestedById: 2,
        decidedById: 1,
        decisionNote: '확인 완료',
        createdAt: _now.subtract(const Duration(days: 1, hours: 1)),
      ),
    ]);
  }

  final DateTime _now;
  final List<OperatorScheduleEntry> _entries = <OperatorScheduleEntry>[];
  final List<OperatorScheduleChangeRequest> _changes =
      <OperatorScheduleChangeRequest>[];
  int _nextEntryId = 100;
  int _nextChangeId = 100;

  @override
  List<OperatorScheduleEntry> listEntries() {
    final rows = _entries.toList()
      ..sort((a, b) {
        final byDate = a.workDate.compareTo(b.workDate);
        if (byDate != 0) return byDate;
        return _minutesOf(a.startTime).compareTo(_minutesOf(b.startTime));
      });
    return List<OperatorScheduleEntry>.unmodifiable(rows);
  }

  @override
  List<OperatorScheduleChangeRequest> listChanges({
    ScheduleChangeStatus? status,
  }) {
    final rows =
        _changes.where((c) => status == null || c.status == status).toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return List<OperatorScheduleChangeRequest>.unmodifiable(rows);
  }

  @override
  OperatorScheduleEntry createDraft({
    required DateTime workDate,
    required String castId,
    required TimeOfDay startTime,
    required TimeOfDay endTime,
    String note = '',
  }) {
    final date = DateTime(workDate.year, workDate.month, workDate.day);
    final entry = OperatorScheduleEntry(
      id: 'entry-${_nextEntryId++}',
      workDate: date,
      castId: castId,
      startTime: startTime,
      endTime: endTime,
      status: ScheduleEntryStatus.draft,
      note: note,
      createdAt: _now,
      updatedAt: _now,
    );
    _entries.add(entry);
    return entry;
  }

  @override
  OperatorScheduleEntry editDraft({
    required String entryId,
    TimeOfDay? startTime,
    TimeOfDay? endTime,
    String? note,
  }) {
    final index = _requireIndex(entryId);
    if (_entries[index].status != ScheduleEntryStatus.draft) {
      throw StateError('Only draft entries can be edited directly.');
    }
    final updated = _entries[index].copyWith(
      startTime: startTime,
      endTime: endTime,
      note: note,
      updatedAt: _now,
    );
    _entries[index] = updated;
    return updated;
  }

  @override
  OperatorScheduleEntry publishEntry(String entryId) {
    final index = _requireIndex(entryId);
    final updated = _entries[index].copyWith(
      status: ScheduleEntryStatus.published,
      updatedAt: _now,
    );
    _entries[index] = updated;
    return updated;
  }

  @override
  OperatorScheduleEntry unpublishEntry({
    required String entryId,
    String reason = '',
  }) {
    final index = _requireIndex(entryId);
    final updated = _entries[index].copyWith(
      status: ScheduleEntryStatus.unpublished,
      updatedAt: _now,
    );
    _entries[index] = updated;
    return updated;
  }

  @override
  OperatorScheduleChangeRequest requestChange({
    required String entryId,
    required Map<String, String> proposed,
    required int requestedById,
    String reason = '',
  }) {
    final entry = _entries[_requireIndex(entryId)];
    if (entry.status != ScheduleEntryStatus.published) {
      throw StateError('Change requests apply to published entries only.');
    }
    _parseProposed(proposed); // Fail fast on bad keys/values, like the server.
    final change = OperatorScheduleChangeRequest(
      id: 'change-${_nextChangeId++}',
      entryId: entryId,
      proposed: Map<String, String>.unmodifiable(proposed),
      before: entry.snapshot(),
      reason: reason,
      status: ScheduleChangeStatus.pending,
      requestedById: requestedById,
      createdAt: _now,
    );
    _changes.add(change);
    return change;
  }

  @override
  OperatorScheduleChangeRequest approveChange({
    required String changeId,
    required int actorId,
    String decisionNote = '',
  }) {
    final index = _requireChangeIndex(changeId);
    final change = _changes[index];
    if (change.status != ScheduleChangeStatus.pending) {
      throw StateError('Only a pending change request can be approved.');
    }
    if (change.requestedById == actorId) {
      // Separation of duties: a change is applied by a *different* operator.
      throw StateError('A change must be approved by a different operator.');
    }
    _applyProposed(change);
    final decided = change.copyWith(
      status: ScheduleChangeStatus.approved,
      decidedById: actorId,
      decisionNote: decisionNote,
    );
    _changes[index] = decided;
    return decided;
  }

  @override
  OperatorScheduleChangeRequest rejectChange({
    required String changeId,
    required int actorId,
    String decisionNote = '',
  }) {
    final index = _requireChangeIndex(changeId);
    final change = _changes[index];
    if (change.status != ScheduleChangeStatus.pending) {
      throw StateError('Only a pending change request can be rejected.');
    }
    final decided = change.copyWith(
      status: ScheduleChangeStatus.rejected,
      decidedById: actorId,
      decisionNote: decisionNote,
    );
    _changes[index] = decided;
    return decided;
  }

  /// Applies an approved change's proposed fields to its target entry.
  void _applyProposed(OperatorScheduleChangeRequest change) {
    final entryIndex = _requireIndex(change.entryId);
    final parsed = _parseProposed(change.proposed);
    _entries[entryIndex] = _entries[entryIndex].copyWith(
      workDate: parsed.workDate,
      startTime: parsed.startTime,
      endTime: parsed.endTime,
      note: parsed.note,
      updatedAt: _now,
    );
  }

  /// The index of [entryId], or a controlled [StateError] when it is unknown
  /// (so a bad id never indexes `_entries[-1]` into a RangeError).
  int _requireIndex(String entryId) {
    final index = _entries.indexWhere((entry) => entry.id == entryId);
    if (index < 0) throw StateError('Unknown entry: $entryId');
    return index;
  }

  int _requireChangeIndex(String changeId) {
    final index = _changes.indexWhere((change) => change.id == changeId);
    if (index < 0) throw StateError('Unknown change: $changeId');
    return index;
  }

  static int _minutesOf(TimeOfDay t) => t.hour * 60 + t.minute;
}

/// Parsed, typed view of a `proposed` map (only the present keys are non-null).
@immutable
class _ParsedProposed {
  const _ParsedProposed({
    this.workDate,
    this.startTime,
    this.endTime,
    this.note,
  });

  final DateTime? workDate;
  final TimeOfDay? startTime;
  final TimeOfDay? endTime;
  final String? note;
}

/// Validates proposed keys and parses values into typed entry fields.
///
/// Mirrors the server's `_parse_proposed`: unknown keys and unparseable
/// date/time strings raise [FormatException] so a bad change is rejected at
/// request time rather than sitting pending forever.
_ParsedProposed _parseProposed(Map<String, String> proposed) {
  final unknown = proposed.keys.where((k) => !kChangeableFields.contains(k));
  if (unknown.isNotEmpty) {
    throw FormatException('Unchangeable fields: ${unknown.toList()}');
  }
  return _ParsedProposed(
    workDate: proposed.containsKey('work_date')
        ? parseScheduleDate(proposed['work_date']!)
        : null,
    startTime: proposed.containsKey('start_time')
        ? parseScheduleTime(proposed['start_time']!)
        : null,
    endTime: proposed.containsKey('end_time')
        ? parseScheduleTime(proposed['end_time']!)
        : null,
    note: proposed['note'],
  );
}

/// Parses a strict ISO `YYYY-MM-DD` date, rejecting datetime-shaped or
/// non-zero-padded input the server's `date.fromisoformat` would reject.
///
/// Throws [FormatException] for any other shape, so a `work_date` change that
/// the server would 400 is rejected here at request time too.
DateTime parseScheduleDate(String value) {
  final parts = value.split('-');
  if (parts.length != 3) {
    throw FormatException('Invalid date: $value');
  }
  final year = int.tryParse(parts[0]);
  final month = int.tryParse(parts[1]);
  final day = int.tryParse(parts[2]);
  if (year == null || month == null || day == null) {
    throw FormatException('Invalid date: $value');
  }
  // Require canonical zero-padded YYYY-MM-DD components within the server's
  // year range, rejecting signs/widths date.fromisoformat also rejects.
  if (year < 1 ||
      year > 9999 ||
      parts[0] != year.toString().padLeft(4, '0') ||
      parts[1] != month.toString().padLeft(2, '0') ||
      parts[2] != day.toString().padLeft(2, '0')) {
    throw FormatException('Invalid date: $value');
  }
  final date = DateTime(year, month, day);
  // Reject overflow dates DateTime silently normalises (e.g. 2026-02-31 would
  // become 2026-03-03), which date.fromisoformat rejects outright.
  if (date.year != year || date.month != month || date.day != day) {
    throw FormatException('Invalid date: $value');
  }
  return date;
}

/// Formats a date as the server's ISO `YYYY-MM-DD`.
String formatScheduleDate(DateTime date) {
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  return '${date.year}-$m-$d';
}

/// Formats a time as the server's ISO `HH:MM:SS` (seconds always `00`).
String formatScheduleTime(TimeOfDay time) {
  final h = time.hour.toString().padLeft(2, '0');
  final m = time.minute.toString().padLeft(2, '0');
  return '$h:$m:00';
}

/// Formats a time as a compact `HH:MM` for display.
String formatScheduleTimeShort(TimeOfDay time) {
  final h = time.hour.toString().padLeft(2, '0');
  final m = time.minute.toString().padLeft(2, '0');
  return '$h:$m';
}

/// Parses an `HH:MM` or `HH:MM:SS` string into a [TimeOfDay].
///
/// Throws [FormatException] for malformed input or out-of-range fields, so the
/// request-change form can surface the same validation the server applies.
TimeOfDay parseScheduleTime(String value) {
  final parts = value.split(':');
  if (parts.length < 2 || parts.length > 3) {
    throw FormatException('Invalid time: $value');
  }
  final hour = int.tryParse(parts[0]);
  final minute = int.tryParse(parts[1]);
  // Validate the seconds component too (the server's time.fromisoformat rejects
  // e.g. 12:30:99); a valid seconds value is then dropped, as TimeOfDay has no
  // seconds.
  final second = parts.length == 3 ? int.tryParse(parts[2]) : 0;
  if (hour == null || minute == null || second == null) {
    throw FormatException('Invalid time: $value');
  }
  if (hour < 0 ||
      hour > 23 ||
      minute < 0 ||
      minute > 59 ||
      second < 0 ||
      second > 59) {
    throw FormatException('Time out of range: $value');
  }
  // Require canonical zero-padded HH:MM[:SS] components, as time.fromisoformat
  // does — this rejects unpadded ('1:02') and signed inputs.
  if (parts[0] != hour.toString().padLeft(2, '0') ||
      parts[1] != minute.toString().padLeft(2, '0') ||
      (parts.length == 3 && parts[2] != second.toString().padLeft(2, '0'))) {
    throw FormatException('Invalid time: $value');
  }
  return TimeOfDay(hour: hour, minute: minute);
}

/// Parses an `HH:MM` string, returning null instead of throwing on bad input
/// (for form validation that distinguishes "empty/invalid" from a valid time).
TimeOfDay? tryParseScheduleTime(String value) {
  try {
    return parseScheduleTime(value.trim());
  } on FormatException {
    return null;
  }
}
