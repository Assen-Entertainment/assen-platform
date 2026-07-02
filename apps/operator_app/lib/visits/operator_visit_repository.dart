import 'package:flutter/foundation.dart';

/// Status values shown by the operator visit list.
enum OperatorVisitStatus {
  /// A valid visit record.
  active,

  /// A record kept for audit but excluded operationally.
  voided,
}

/// Fan option exposed to manual check-in without personal data.
@immutable
class OperatorFanOption {
  /// Creates a selectable fan identity for operator mock flows.
  const OperatorFanOption({required this.id, required this.nickname});

  /// Stable mock fan identifier.
  final String id;

  /// Display nickname; real names and phone numbers stay out of operator UI.
  final String nickname;
}

/// Visit row rendered by the operator check-in screen.
@immutable
class OperatorVisitRecord {
  /// Creates an immutable operator visit row.
  const OperatorVisitRecord({
    required this.id,
    required this.fanId,
    required this.fanNickname,
    required this.visitedAt,
    required this.status,
    this.note = '',
    this.voidReason = '',
  });

  /// Stable record identifier.
  final String id;

  /// Fan identifier used by the repository adapter.
  final String fanId;

  /// Fan nickname displayed in the list.
  final String fanNickname;

  /// Visit timestamp.
  final DateTime visitedAt;

  /// Current lifecycle status.
  final OperatorVisitStatus status;

  /// Operator note, kept out of the row surface unless edited.
  final String note;

  /// Reason captured when the record was voided.
  final String voidReason;

  /// Returns a copy with selected fields replaced.
  OperatorVisitRecord copyWith({
    DateTime? visitedAt,
    OperatorVisitStatus? status,
    String? note,
    String? voidReason,
  }) {
    return OperatorVisitRecord(
      id: id,
      fanId: fanId,
      fanNickname: fanNickname,
      visitedAt: visitedAt ?? this.visitedAt,
      status: status ?? this.status,
      note: note ?? this.note,
      voidReason: voidReason ?? this.voidReason,
    );
  }
}

/// Adapter boundary for operator visit data.
abstract class OperatorVisitRepository {
  /// Fan choices for manual check-in.
  List<OperatorFanOption> fanOptions();

  /// Lists records for [date], including voided rows.
  List<OperatorVisitRecord> listForDate(DateTime date);

  /// Creates a manual check-in for [fanId].
  OperatorVisitRecord recordManualVisit({
    required String fanId,
    required DateTime visitedAt,
    String note,
  });

  /// Corrects editable fields on an existing record.
  OperatorVisitRecord correctVisit({
    required String recordId,
    DateTime? visitedAt,
    String? note,
  });

  /// Voids a record with an operator reason.
  OperatorVisitRecord voidVisit({
    required String recordId,
    required String reason,
  });
}

/// In-memory implementation used until the API client adapter lands.
class InMemoryOperatorVisitRepository implements OperatorVisitRepository {
  /// Creates the mock repository with deterministic visit rows.
  InMemoryOperatorVisitRepository({DateTime? now})
    : _now = now ?? DateTime.now() {
    _records.addAll([
      OperatorVisitRecord(
        id: 'visit-1',
        fanId: 'fan-a',
        fanNickname: '하루',
        visitedAt: DateTime(_now.year, _now.month, _now.day, 11, 20),
        status: OperatorVisitStatus.active,
      ),
      OperatorVisitRecord(
        id: 'visit-2',
        fanId: 'fan-b',
        fanNickname: '미오',
        visitedAt: DateTime(_now.year, _now.month, _now.day, 12, 5),
        status: OperatorVisitStatus.voided,
        voidReason: '중복 입력',
      ),
    ]);
  }

  final DateTime _now;
  final List<OperatorVisitRecord> _records = <OperatorVisitRecord>[];
  int _nextId = 3;

  static const List<OperatorFanOption> _fans = <OperatorFanOption>[
    OperatorFanOption(id: 'fan-a', nickname: '하루'),
    OperatorFanOption(id: 'fan-b', nickname: '미오'),
    OperatorFanOption(id: 'fan-c', nickname: '소라'),
  ];

  @override
  List<OperatorFanOption> fanOptions() => _fans;

  @override
  List<OperatorVisitRecord> listForDate(DateTime date) {
    final rows =
        _records.where((record) => _sameDay(record.visitedAt, date)).toList()
          ..sort((a, b) => b.visitedAt.compareTo(a.visitedAt));
    return List<OperatorVisitRecord>.unmodifiable(rows);
  }

  @override
  OperatorVisitRecord recordManualVisit({
    required String fanId,
    required DateTime visitedAt,
    String note = '',
  }) {
    final fan = _fans.firstWhere((option) => option.id == fanId);
    final record = OperatorVisitRecord(
      id: 'visit-${_nextId++}',
      fanId: fan.id,
      fanNickname: fan.nickname,
      visitedAt: visitedAt,
      status: OperatorVisitStatus.active,
      note: note,
    );
    _records.add(record);
    return record;
  }

  @override
  OperatorVisitRecord correctVisit({
    required String recordId,
    DateTime? visitedAt,
    String? note,
  }) {
    final index = _records.indexWhere((record) => record.id == recordId);
    final corrected = _records[index].copyWith(
      visitedAt: visitedAt,
      note: note,
    );
    _records[index] = corrected;
    return corrected;
  }

  @override
  OperatorVisitRecord voidVisit({
    required String recordId,
    required String reason,
  }) {
    final index = _records.indexWhere((record) => record.id == recordId);
    final voided = _records[index].copyWith(
      status: OperatorVisitStatus.voided,
      voidReason: reason,
    );
    _records[index] = voided;
    return voided;
  }

  bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}
