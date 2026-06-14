import 'package:flutter/foundation.dart';

/// Sentinel placed in a withheld value so the surface shape is stable (the
/// field still exists, but reads as redacted) — mirrors the server's
/// `admin_rbac.redaction.REDACTED`.
const String kRedactedValue = '[redacted]';

/// Viewer role for the operator safety console — the RBAC surface seam.
///
/// Mirrors the server's two-tier access (`admin_rbac`): an [operator] may list
/// and triage report summaries with the detail fields redacted; a [manager] may
/// also read the restricted narrative and resolve / block. Real role claims
/// arrive with the auth token in a later issue (see `operator_router` P3b);
/// until then this is the presentation seam that lets the redaction surface
/// be exercised in the mock.
enum SafetyViewerRole {
  /// operator+ — list/triage with detail fields redacted.
  operator,

  /// manager+ — additionally reads the narrative and resolves / blocks.
  manager,
}

/// Report category (mirrors server `safety.ReportType` — a closed taxonomy).
enum OperatorReportType {
  /// 원치 않는 요청.
  unwantedRequest,

  /// 사적 연락 시도.
  privateContact,

  /// 외부 만남 유도.
  externalMeeting,

  /// 폭언·모욕.
  verbalAbuse,

  /// 폭력·위협.
  physicalThreat,

  /// 촬영 규칙 위반.
  photoViolation,

  /// 스토킹 우려.
  stalkingConcern,

  /// 환불 분쟁.
  refundDispute,

  /// 사생활·초상권 우려.
  privacyPortraitConcern,

  /// 사기·부정 이용.
  fraudAbuse,

  /// 기타.
  other,
}

/// The Korean label for an [OperatorReportType].
extension OperatorReportTypeLabel on OperatorReportType {
  /// The human-readable report-type label.
  String get label => switch (this) {
    OperatorReportType.unwantedRequest => '원치 않는 요청',
    OperatorReportType.privateContact => '사적 연락 시도',
    OperatorReportType.externalMeeting => '외부 만남 유도',
    OperatorReportType.verbalAbuse => '폭언·모욕',
    OperatorReportType.physicalThreat => '폭력·위협',
    OperatorReportType.photoViolation => '촬영 규칙 위반',
    OperatorReportType.stalkingConcern => '스토킹 우려',
    OperatorReportType.refundDispute => '환불 분쟁',
    OperatorReportType.privacyPortraitConcern => '사생활·초상권 우려',
    OperatorReportType.fraudAbuse => '사기·부정 이용',
    OperatorReportType.other => '기타',
  };
}

/// Report severity (mirrors server `safety.ReportSeverity`).
enum OperatorReportSeverity {
  /// 낮음.
  low,

  /// 보통.
  medium,

  /// 높음.
  high,

  /// 심각.
  critical,
}

/// The Korean label for an [OperatorReportSeverity].
extension OperatorReportSeverityLabel on OperatorReportSeverity {
  /// The human-readable severity label.
  String get label => switch (this) {
    OperatorReportSeverity.low => '낮음',
    OperatorReportSeverity.medium => '보통',
    OperatorReportSeverity.high => '높음',
    OperatorReportSeverity.critical => '심각',
  };
}

/// Handling lifecycle (mirrors server `safety.ReportStatus`): 접수→검토→조치→종료.
enum OperatorReportStatus {
  /// 접수 — received.
  received,

  /// 검토중 — reviewing.
  reviewing,

  /// 조치 — actioned.
  actioned,

  /// 종료 — closed (reached only via resolve; never reopened).
  closed,
}

/// The Korean label for an [OperatorReportStatus].
extension OperatorReportStatusLabel on OperatorReportStatus {
  /// The human-readable status label.
  String get label => switch (this) {
    OperatorReportStatus.received => '접수',
    OperatorReportStatus.reviewing => '검토중',
    OperatorReportStatus.actioned => '조치',
    OperatorReportStatus.closed => '종료',
  };
}

/// Who may see the detail fields (mirrors server `safety.ReportVisibility`).
enum OperatorReportVisibility {
  /// 제한 — restricted (low/medium severity).
  restricted,

  /// 매니저 전용 — manager-only (high/critical severity).
  managerOnly,
}

/// The Korean label for an [OperatorReportVisibility].
extension OperatorReportVisibilityLabel on OperatorReportVisibility {
  /// The human-readable visibility label.
  String get label => switch (this) {
    OperatorReportVisibility.restricted => '제한',
    OperatorReportVisibility.managerOnly => '매니저 전용',
  };
}

/// What a block restricts (mirrors server `safety.BlockScope`).
enum OperatorBlockScope {
  /// 예약 — reservation.
  reservation,

  /// 팬덤 기능 — fandom feature.
  fandomFeature,

  /// 매장 방문 — store visit.
  storeVisit,

  /// 전체 — all surfaces.
  all,
}

/// The Korean label for an [OperatorBlockScope].
extension OperatorBlockScopeLabel on OperatorBlockScope {
  /// The human-readable scope label.
  String get label => switch (this) {
    OperatorBlockScope.reservation => '예약',
    OperatorBlockScope.fandomFeature => '팬덤 기능',
    OperatorBlockScope.storeVisit => '매장 방문',
    OperatorBlockScope.all => '전체',
  };
}

/// Closed reason codes for a block (mirrors server `safety.BlockReason`).
///
/// A closed enum, never free text, so a block carries no narrative or PII — the
/// same value-level guard the server enforces.
enum OperatorBlockReason {
  /// 정책 위반 — policy violation.
  policyViolation,

  /// 안전 위험 — safety risk.
  safetyRisk,

  /// 괴롭힘 — harassment.
  harassment,

  /// 사기 — fraud.
  fraud,

  /// 분쟁 — dispute.
  dispute,

  /// 기타 — other.
  other,
}

/// The Korean label for an [OperatorBlockReason].
extension OperatorBlockReasonLabel on OperatorBlockReason {
  /// The human-readable reason label.
  String get label => switch (this) {
    OperatorBlockReason.policyViolation => '정책 위반',
    OperatorBlockReason.safetyRisk => '안전 위험',
    OperatorBlockReason.harassment => '괴롭힘',
    OperatorBlockReason.fraud => '사기',
    OperatorBlockReason.dispute => '분쟁',
    OperatorBlockReason.other => '기타',
  };
}

/// A safety report row rendered by the operator console.
///
/// Holds the full record; the [SafetyReportRedaction] extension produces the
/// role-appropriate view, so the detail fields (reporter/target/narrative) are
/// only read through a redaction-aware getter — never directly in the UI.
/// [targetBlocked] / [riskFlagCount] are the operational annotations a block
/// action leaves behind (the server's `has_active_block` predicate, surfaced).
@immutable
class OperatorSafetyReport {
  /// Creates an immutable operator safety report row.
  const OperatorSafetyReport({
    required this.id,
    required this.type,
    required this.severity,
    required this.status,
    required this.visibility,
    required this.createdAt,
    required this.reporterRef,
    required this.targetRef,
    required this.narrative,
    this.resolutionNote = '',
    this.targetBlocked = false,
    this.riskFlagCount = 0,
  });

  /// Stable report identifier.
  final String id;

  /// The report category.
  final OperatorReportType type;

  /// Severity; high/critical force [OperatorReportVisibility.managerOnly].
  final OperatorReportSeverity severity;

  /// Current handling status.
  final OperatorReportStatus status;

  /// Who may see the detail fields.
  final OperatorReportVisibility visibility;

  /// When the report was filed.
  final DateTime createdAt;

  /// Reporter descriptor — a **detail field** (redacted for operators).
  final String reporterRef;

  /// Target descriptor — a **detail field** (redacted for operators).
  final String targetRef;

  /// The restricted narrative — manager+ only; never shown to operators.
  final String narrative;

  /// The resolution note captured at close — a **detail field** (manager+).
  final String resolutionNote;

  /// Whether the target carries an active hard block (surfaced on the card).
  final bool targetBlocked;

  /// How many risk flags the target carries (surfaced on the card).
  final int riskFlagCount;

  /// Returns a copy with selected fields replaced.
  OperatorSafetyReport copyWith({
    OperatorReportStatus? status,
    String? resolutionNote,
    bool? targetBlocked,
    int? riskFlagCount,
  }) {
    return OperatorSafetyReport(
      id: id,
      type: type,
      severity: severity,
      status: status ?? this.status,
      visibility: visibility,
      createdAt: createdAt,
      reporterRef: reporterRef,
      targetRef: targetRef,
      narrative: narrative,
      resolutionNote: resolutionNote ?? this.resolutionNote,
      targetBlocked: targetBlocked ?? this.targetBlocked,
      riskFlagCount: riskFlagCount ?? this.riskFlagCount,
    );
  }
}

/// Field-level redaction for a report by viewer role.
///
/// Mirrors the server's `redact_safety_report`: a manager sees everything, an
/// operator gets [kRedactedValue] for the detail fields (reporter / target /
/// narrative / resolution note). Keeping the policy in one transform — rather
/// than scattered `if (role)` checks across the widgets — matches the server's
/// "redaction in one place" design.
extension SafetyReportRedaction on OperatorSafetyReport {
  /// Whether [role] may read the manager-only detail fields.
  bool canViewDetail(SafetyViewerRole role) => role == SafetyViewerRole.manager;

  /// The reporter descriptor for [role] (redacted for operators).
  String reporterRefFor(SafetyViewerRole role) =>
      canViewDetail(role) ? reporterRef : kRedactedValue;

  /// The target descriptor for [role] (redacted for operators).
  String targetRefFor(SafetyViewerRole role) =>
      canViewDetail(role) ? targetRef : kRedactedValue;

  /// The narrative for [role] (redacted for operators).
  String narrativeFor(SafetyViewerRole role) =>
      canViewDetail(role) ? narrative : kRedactedValue;

  /// The resolution note for [role] (redacted for operators).
  String resolutionNoteFor(SafetyViewerRole role) =>
      canViewDetail(role) ? resolutionNote : kRedactedValue;
}

/// A block / risk-flag the operator console can create on a target.
@immutable
class OperatorUserBlock {
  /// Creates an immutable block record.
  const OperatorUserBlock({
    required this.id,
    required this.targetRef,
    required this.scope,
    required this.reason,
    required this.isRiskFlag,
    required this.createdAt,
    required this.sourceReportId,
  });

  /// Stable block identifier.
  final String id;

  /// The blocked target descriptor.
  final String targetRef;

  /// What the block restricts.
  final OperatorBlockScope scope;

  /// Why the block was applied (closed reason code).
  final OperatorBlockReason reason;

  /// Whether this is a soft risk flag rather than a hard block.
  final bool isRiskFlag;

  /// When the block was created.
  final DateTime createdAt;

  /// The report the block was raised from.
  final String sourceReportId;
}

/// Adapter boundary for operator safety data (the API client lands later,
/// behind this same surface — mirroring the ASS-96 server contract).
abstract class OperatorSafetyRepository {
  /// Lists safety reports, newest first.
  List<OperatorSafetyReport> listReports();

  /// Lists the blocks created so far (newest first).
  List<OperatorUserBlock> listBlocks();

  /// Advances a report's handling status (received→reviewing→actioned).
  ///
  /// Throws [ArgumentError] for an attempt to set [OperatorReportStatus.closed]
  /// (use [resolveReport]) and [StateError] for a change on an already-closed
  /// report — mirroring the server's `change_report_status` guards.
  OperatorSafetyReport advanceStatus({
    required String reportId,
    required OperatorReportStatus status,
  });

  /// Closes a report (manager+); the note lands in the restricted detail.
  ///
  /// Throws [StateError] when the report is already closed.
  OperatorSafetyReport resolveReport({
    required String reportId,
    required String resolutionNote,
  });

  /// Blocks (or risk-flags) the target of [reportId] (manager+).
  ///
  /// Mirrors the server's `block_user`: the block is recorded and the target's
  /// annotation is surfaced on every report about that target.
  OperatorUserBlock blockUser({
    required String reportId,
    required OperatorBlockScope scope,
    required OperatorBlockReason reason,
    required bool isRiskFlag,
  });
}

/// In-memory implementation used until the API client adapter lands.
class InMemoryOperatorSafetyRepository implements OperatorSafetyRepository {
  /// Creates the mock repository with deterministic rows.
  ///
  /// [now] anchors the relative timestamps so widget tests are stable.
  InMemoryOperatorSafetyRepository({DateTime? now})
    : _now = now ?? DateTime.now() {
    _reports.addAll([
      OperatorSafetyReport(
        id: 'report-1',
        type: OperatorReportType.privateContact,
        severity: OperatorReportSeverity.high,
        status: OperatorReportStatus.received,
        visibility: OperatorReportVisibility.managerOnly,
        createdAt: _now.subtract(const Duration(hours: 2)),
        reporterRef: '캐스트 미오',
        targetRef: '팬 A12',
        narrative: '행사 종료 후 사적 연락처를 반복적으로 요구함.',
        riskFlagCount: 1,
      ),
      OperatorSafetyReport(
        id: 'report-2',
        type: OperatorReportType.photoViolation,
        severity: OperatorReportSeverity.medium,
        status: OperatorReportStatus.reviewing,
        visibility: OperatorReportVisibility.restricted,
        createdAt: _now.subtract(const Duration(days: 1, hours: 3)),
        reporterRef: '운영자',
        targetRef: '팬 B7',
        narrative: '금지 구역에서 촬영을 시도하여 1차 안내함.',
      ),
      OperatorSafetyReport(
        id: 'report-3',
        type: OperatorReportType.refundDispute,
        severity: OperatorReportSeverity.low,
        status: OperatorReportStatus.actioned,
        visibility: OperatorReportVisibility.restricted,
        createdAt: _now.subtract(const Duration(days: 2, hours: 5)),
        reporterRef: '팬 C3',
        targetRef: '매장',
        narrative: '환불 처리 지연에 대한 이의 제기. 매니저 검토 후 환불 완료.',
      ),
      OperatorSafetyReport(
        id: 'report-4',
        type: OperatorReportType.fraudAbuse,
        severity: OperatorReportSeverity.critical,
        status: OperatorReportStatus.closed,
        visibility: OperatorReportVisibility.managerOnly,
        createdAt: _now.subtract(const Duration(days: 5)),
        reporterRef: '운영자',
        targetRef: '팬 D9',
        narrative: '쿠폰 부정 사용 정황 확인.',
        resolutionNote: '예약 기능 제한 처리 완료.',
        targetBlocked: true,
      ),
    ]);
  }

  final DateTime _now;
  final List<OperatorSafetyReport> _reports = <OperatorSafetyReport>[];
  final List<OperatorUserBlock> _blocks = <OperatorUserBlock>[];
  int _nextBlockId = 1;

  @override
  List<OperatorSafetyReport> listReports() {
    final rows = _reports.toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return List<OperatorSafetyReport>.unmodifiable(rows);
  }

  @override
  List<OperatorUserBlock> listBlocks() =>
      List<OperatorUserBlock>.unmodifiable(_blocks.reversed);

  /// The index of [reportId], or a controlled [StateError] when it is unknown
  /// (so a bad id never indexes `_reports[-1]` into a RangeError).
  int _requireIndex(String reportId) {
    final index = _reports.indexWhere((report) => report.id == reportId);
    if (index < 0) {
      throw StateError('Unknown report: $reportId');
    }
    return index;
  }

  @override
  OperatorSafetyReport advanceStatus({
    required String reportId,
    required OperatorReportStatus status,
  }) {
    // The controller only ever passes nextStatusAfter(current); the repository
    // mirrors the server's change_report_status (reject closed here / from a
    // closed report) without re-deriving the monotonic order.
    if (status == OperatorReportStatus.closed) {
      throw ArgumentError.value(
        status,
        'status',
        'Use resolveReport to close a report.',
      );
    }
    final index = _requireIndex(reportId);
    if (_reports[index].status == OperatorReportStatus.closed) {
      throw StateError('Closed report cannot change status.');
    }
    final updated = _reports[index].copyWith(status: status);
    _reports[index] = updated;
    return updated;
  }

  @override
  OperatorSafetyReport resolveReport({
    required String reportId,
    required String resolutionNote,
  }) {
    final index = _requireIndex(reportId);
    if (_reports[index].status == OperatorReportStatus.closed) {
      throw StateError('Report is already closed.');
    }
    final updated = _reports[index].copyWith(
      status: OperatorReportStatus.closed,
      resolutionNote: resolutionNote,
    );
    _reports[index] = updated;
    return updated;
  }

  @override
  OperatorUserBlock blockUser({
    required String reportId,
    required OperatorBlockScope scope,
    required OperatorBlockReason reason,
    required bool isRiskFlag,
  }) {
    final source = _reports[_requireIndex(reportId)];
    final block = OperatorUserBlock(
      id: 'block-${_nextBlockId++}',
      targetRef: source.targetRef,
      scope: scope,
      reason: reason,
      isRiskFlag: isRiskFlag,
      createdAt: _now,
      sourceReportId: reportId,
    );
    _blocks.add(block);
    // Surface the block on every report about the same target (the server's
    // has_active_block predicate is per-target, not per-report).
    for (var i = 0; i < _reports.length; i++) {
      if (_reports[i].targetRef != source.targetRef) continue;
      _reports[i] = isRiskFlag
          ? _reports[i].copyWith(riskFlagCount: _reports[i].riskFlagCount + 1)
          : _reports[i].copyWith(targetBlocked: true);
    }
    return block;
  }
}
