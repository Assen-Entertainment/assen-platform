import 'package:flutter/foundation.dart';

/// Lifecycle status shown by the operator cheki list.
enum OperatorChekiStatus {
  /// A valid cheki record.
  active,

  /// A record kept for audit/reconciliation but excluded operationally.
  voided,
}

/// Cast option exposed to cheki entry without personal data.
@immutable
class OperatorCastOption {
  /// Creates a selectable cast identity for operator mock flows.
  const OperatorCastOption({required this.id, required this.name});

  /// Stable mock cast identifier.
  final String id;

  /// Display name shown in the cast picker.
  final String name;
}

/// Cheki row rendered by the operator cheki screen.
@immutable
class OperatorChekiRecord {
  /// Creates an immutable operator cheki row.
  const OperatorChekiRecord({
    required this.id,
    required this.castId,
    required this.castName,
    required this.chekiType,
    required this.quantity,
    required this.status,
    this.voidReason = '',
  });

  /// Stable record identifier.
  final String id;

  /// Cast identifier the cheki is attributed to.
  final String castId;

  /// Cast display name for the list.
  final String castName;

  /// Cheki kind (basic/option/event/comp/test).
  final String chekiType;

  /// Number of cheki in this record.
  final int quantity;

  /// Current lifecycle status.
  final OperatorChekiStatus status;

  /// Reason captured when the record was voided.
  final String voidReason;

  /// Returns a copy with selected fields replaced.
  OperatorChekiRecord copyWith({
    String? chekiType,
    int? quantity,
    OperatorChekiStatus? status,
    String? voidReason,
  }) {
    return OperatorChekiRecord(
      id: id,
      castId: castId,
      castName: castName,
      chekiType: chekiType ?? this.chekiType,
      quantity: quantity ?? this.quantity,
      status: status ?? this.status,
      voidReason: voidReason ?? this.voidReason,
    );
  }
}

/// Adapter boundary for operator cheki data (API client lands later).
abstract class OperatorChekiRepository {
  /// Cast choices for cheki entry.
  List<OperatorCastOption> castOptions();

  /// Cheki kinds selectable in the entry dialog.
  List<String> chekiTypes();

  /// Lists today's cheki records, including voided rows.
  List<OperatorChekiRecord> listToday();

  /// Records a cheki for [castId].
  OperatorChekiRecord recordCheki({
    required String castId,
    required String chekiType,
    required int quantity,
  });

  /// Corrects the quantity on an existing record.
  OperatorChekiRecord correctCheki({
    required String recordId,
    required int quantity,
  });

  /// Voids a record with an operator reason.
  OperatorChekiRecord voidCheki({
    required String recordId,
    required String reason,
  });
}

/// In-memory implementation used until the API client adapter lands.
class InMemoryOperatorChekiRepository implements OperatorChekiRepository {
  /// Creates the mock repository with deterministic cheki rows.
  InMemoryOperatorChekiRepository() {
    _records.addAll([
      const OperatorChekiRecord(
        id: 'cheki-1',
        castId: 'mio',
        castName: '미오',
        chekiType: 'basic',
        quantity: 2,
        status: OperatorChekiStatus.active,
      ),
      const OperatorChekiRecord(
        id: 'cheki-2',
        castId: 'yuki',
        castName: '유키',
        chekiType: 'event',
        quantity: 1,
        status: OperatorChekiStatus.voided,
        voidReason: '중복 입력',
      ),
    ]);
  }

  final List<OperatorChekiRecord> _records = <OperatorChekiRecord>[];
  int _nextId = 3;

  static const List<OperatorCastOption> _casts = <OperatorCastOption>[
    OperatorCastOption(id: 'mio', name: '미오'),
    OperatorCastOption(id: 'yuki', name: '유키'),
    OperatorCastOption(id: 'moka', name: '모카'),
  ];

  static const List<String> _types = <String>[
    'basic',
    'option',
    'event',
    'comp',
  ];

  @override
  List<OperatorCastOption> castOptions() => _casts;

  @override
  List<String> chekiTypes() => _types;

  @override
  List<OperatorChekiRecord> listToday() =>
      List<OperatorChekiRecord>.unmodifiable(_records);

  @override
  OperatorChekiRecord recordCheki({
    required String castId,
    required String chekiType,
    required int quantity,
  }) {
    final cast = _casts.firstWhere((option) => option.id == castId);
    final record = OperatorChekiRecord(
      id: 'cheki-${_nextId++}',
      castId: cast.id,
      castName: cast.name,
      chekiType: chekiType,
      quantity: quantity,
      status: OperatorChekiStatus.active,
    );
    _records.add(record);
    return record;
  }

  @override
  OperatorChekiRecord correctCheki({
    required String recordId,
    required int quantity,
  }) {
    final index = _records.indexWhere((record) => record.id == recordId);
    final corrected = _records[index].copyWith(quantity: quantity);
    _records[index] = corrected;
    return corrected;
  }

  @override
  OperatorChekiRecord voidCheki({
    required String recordId,
    required String reason,
  }) {
    final index = _records.indexWhere((record) => record.id == recordId);
    final voided = _records[index].copyWith(
      status: OperatorChekiStatus.voided,
      voidReason: reason,
    );
    _records[index] = voided;
    return voided;
  }
}
