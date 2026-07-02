import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/safety/operator_safety_providers.dart';
import 'package:operator_app/safety/operator_safety_repository.dart';
import 'package:ui_kit/ui_kit.dart';

/// O4 operator safety-report console (신고 처리).
///
/// Lists safety reports filtered by a 접수 / 처리중 / 종료 status bucket, surfaces the
/// classification badges, and opens a per-report detail dialog for the handling
/// actions (status transition, narrative view, resolve, block). The detail and
/// narrative are RBAC-gated: an operator sees the detail fields redacted,
/// while a manager reads the narrative and may resolve / block — mirroring
/// the ASS-96 server redaction contract (see [safetyViewerRoleProvider]).
class OperatorReportsScreen extends ConsumerStatefulWidget {
  /// Creates the safety-report console.
  const OperatorReportsScreen({super.key});

  @override
  ConsumerState<OperatorReportsScreen> createState() =>
      _OperatorReportsScreenState();
}

class _OperatorReportsScreenState extends ConsumerState<OperatorReportsScreen> {
  /// Status buckets, in segment order: 접수 / 처리중 / 종료.
  static const List<String> _bucketLabels = ['접수', '처리중', '종료'];

  int _selectedBucket = 0;

  /// The bucket index a [status] falls into (검토중·조치 share the 처리중 bucket).
  static int _bucketOf(OperatorReportStatus status) => switch (status) {
    OperatorReportStatus.received => 0,
    OperatorReportStatus.reviewing => 1,
    OperatorReportStatus.actioned => 1,
    OperatorReportStatus.closed => 2,
  };

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final role = ref.watch(safetyViewerRoleProvider);
    final reports = ref.watch(operatorSafetyControllerProvider);

    final counts = <int>[0, 0, 0];
    for (final report in reports) {
      counts[_bucketOf(report.status)]++;
    }
    final segments = [
      for (var i = 0; i < _bucketLabels.length; i++)
        '${_bucketLabels[i]} ${counts[i]}',
    ];
    final visible = reports
        .where((report) => _bucketOf(report.status) == _selectedBucket)
        .toList();

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '하츠코이'),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.screenMargin,
            SpacingTokens.s5,
            SpacingTokens.screenMargin,
            SpacingTokens.s8,
          ),
          children: [
            Text(
              '신고 처리',
              style: TextStyle(
                color: colors.ink900,
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: SpacingTokens.s4),
            AssenSegmentedTabs(
              segments: segments,
              selectedIndex: _selectedBucket,
              onChanged: (index) => setState(() => _selectedBucket = index),
            ),
            const SizedBox(height: SpacingTokens.s5),
            if (visible.isEmpty)
              _EmptyReportList(colors: colors)
            else
              for (final report in visible) ...[
                _ReportCard(
                  report: report,
                  role: role,
                  onTap: () => _showReportDetail(context, report.id),
                ),
                const SizedBox(height: SpacingTokens.s3),
              ],
            const SizedBox(height: SpacingTokens.s2),
            const AssenNoticeBar(
              kind: AssenNoticeKind.warning,
              message: '모든 상태 변경은 감사 로그에 기록돼요.',
            ),
          ],
        ),
      ),
    );
  }
}

/// A single report card: classification badges + type title + reporter meta.
class _ReportCard extends StatelessWidget {
  const _ReportCard({
    required this.report,
    required this.role,
    required this.onTap,
  });

  final OperatorSafetyReport report;
  final SafetyViewerRole role;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AssenBadge(
                label: report.severity.label,
                hue: _severityHue(report.severity),
              ),
              const SizedBox(width: SpacingTokens.s2),
              AssenBadge(
                label: report.status.label,
                hue: _statusHue(report.status),
              ),
              const Spacer(),
              Text(
                _relativeTime(report.createdAt),
                style: TextStyle(
                  color: colors.ink500,
                  fontSize: TypographyTokens.bodySSize,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s3),
          Text(
            '${report.type.label} 신고',
            style: TextStyle(
              color: colors.ink900,
              fontSize: TypographyTokens.bodyLSize,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: SpacingTokens.s1),
          Text(
            '신고자: ${report.reporterRefFor(role)}',
            style: TextStyle(
              color: colors.ink700,
              fontSize: TypographyTokens.bodySSize,
            ),
          ),
          if (report.targetBlocked || report.riskFlagCount > 0) ...[
            const SizedBox(height: SpacingTokens.s2),
            Wrap(
              spacing: SpacingTokens.s2,
              children: [
                if (report.targetBlocked)
                  const AssenBadge(label: '차단됨', hue: AssenBadgeHue.peach),
                if (report.riskFlagCount > 0)
                  AssenBadge(
                    label: '위험 플래그 ${report.riskFlagCount}',
                    hue: AssenBadgeHue.lemon,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _EmptyReportList extends StatelessWidget {
  const _EmptyReportList({required this.colors});

  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(SpacingTokens.s5),
      decoration: BoxDecoration(
        color: colors.white,
        border: Border.all(color: colors.ink100),
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
      ),
      child: Text(
        '해당 상태의 신고가 없습니다.',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: colors.ink700,
          fontSize: TypographyTokens.bodyMSize,
        ),
      ),
    );
  }
}

Future<void> _showReportDetail(BuildContext context, String reportId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _ReportDetailDialog(reportId: reportId),
  );
}

/// The per-report detail + actions dialog.
///
/// Re-reads the live report from the controller by id, so status / block
/// changes made from its own action sheets reflect immediately. The narrative
/// and detail fields are read through the redaction-aware getters, so an
/// operator only ever sees [kRedactedValue]. Manager-only actions (resolve,
/// block) are hidden for operators.
class _ReportDetailDialog extends ConsumerWidget {
  const _ReportDetailDialog({required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final role = ref.watch(safetyViewerRoleProvider);
    final reports = ref.watch(operatorSafetyControllerProvider);
    OperatorSafetyReport? found;
    for (final candidate in reports) {
      if (candidate.id == reportId) {
        found = candidate;
        break;
      }
    }
    if (found == null) {
      return AlertDialog(
        title: const Text('신고'),
        content: const Text('신고를 찾을 수 없습니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('닫기'),
          ),
        ],
      );
    }
    // A final, non-null local promotes into the action closures below (so the
    // advance button needs no force-unwrap); each rebuild re-resolves it fresh.
    final report = found;

    final controller = ref.read(operatorSafetyControllerProvider.notifier);
    final isManager = report.canViewDetail(role);
    final next = controller.nextStatusAfter(report.status);
    final advanceLabel = _advanceLabel(next);

    return AlertDialog(
      title: Text('${report.type.label} 신고'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssenKeyValueRow(label: '심각도', value: report.severity.label),
            AssenKeyValueRow(label: '상태', value: report.status.label),
            AssenKeyValueRow(label: '공개 범위', value: report.visibility.label),
            AssenKeyValueRow(
              label: '접수 시각',
              value: _formatDateTime(report.createdAt),
            ),
            AssenKeyValueRow(
              label: '신고자',
              value: report.reporterRefFor(role),
            ),
            AssenKeyValueRow(label: '대상', value: report.targetRefFor(role)),
            const SizedBox(height: SpacingTokens.s2),
            const Text(
              '신고 내용',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: SpacingTokens.s1),
            _NarrativeBlock(report: report, role: role),
            if (report.status == OperatorReportStatus.closed)
              AssenKeyValueRow(
                label: '처리 메모',
                value: report.resolutionNoteFor(role),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('닫기'),
        ),
        if (isManager && report.status != OperatorReportStatus.closed)
          TextButton(
            onPressed: () => _openBlockSheet(context, reportId),
            child: const Text('차단 / 위험 플래그'),
          ),
        if (isManager && report.status == OperatorReportStatus.actioned)
          TextButton(
            onPressed: () => _openResolveSheet(context, reportId),
            child: const Text('종료'),
          ),
        if (advanceLabel != null)
          FilledButton(
            onPressed: () => controller.advanceStatus(report),
            child: Text(advanceLabel),
          ),
      ],
    );
  }

  static String? _advanceLabel(OperatorReportStatus? next) => switch (next) {
    OperatorReportStatus.reviewing => '검토 시작',
    OperatorReportStatus.actioned => '조치 완료',
    _ => null,
  };
}

/// The narrative panel — the report text for a manager, [kRedactedValue] for an
/// operator (with a short explanation of the gate).
class _NarrativeBlock extends StatelessWidget {
  const _NarrativeBlock({required this.report, required this.role});

  final OperatorSafetyReport report;
  final SafetyViewerRole role;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final canView = report.canViewDetail(role);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(SpacingTokens.s3),
      decoration: BoxDecoration(
        color: canView ? colors.cream50 : colors.cream200,
        border: Border.all(color: colors.ink100),
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.sm)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            report.narrativeFor(role),
            style: TextStyle(
              color: canView ? colors.ink900 : colors.ink500,
              fontSize: TypographyTokens.bodyMSize,
              height: 1.4,
            ),
          ),
          const SizedBox(height: SpacingTokens.s1),
          Text(
            canView ? '열람 기록은 감사 로그에 남습니다.' : '서사는 매니저 이상만 열람할 수 있습니다.',
            style: TextStyle(
              color: colors.ink500,
              fontSize: TypographyTokens.bodySSize,
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> _openResolveSheet(BuildContext context, String reportId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _ResolveReportDialog(reportId: reportId),
  );
}

Future<void> _openBlockSheet(BuildContext context, String reportId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _BlockTargetDialog(reportId: reportId),
  );
}

/// Close-out dialog: an optional resolution note kept in the restricted store.
class _ResolveReportDialog extends ConsumerStatefulWidget {
  const _ResolveReportDialog({required this.reportId});

  final String reportId;

  @override
  ConsumerState<_ResolveReportDialog> createState() =>
      _ResolveReportDialogState();
}

class _ResolveReportDialogState extends ConsumerState<_ResolveReportDialog> {
  final _noteController = TextEditingController();

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('신고 종료'),
      content: TextField(
        controller: _noteController,
        decoration: const InputDecoration(labelText: '처리 메모 (선택)'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: () {
            final messenger = ScaffoldMessenger.of(context);
            ref
                .read(operatorSafetyControllerProvider.notifier)
                .resolveReport(
                  reportId: widget.reportId,
                  resolutionNote: _noteController.text.trim(),
                );
            Navigator.of(context).pop();
            messenger.showSnackBar(
              const SnackBar(content: Text('신고를 종료했습니다.')),
            );
          },
          child: const Text('종료'),
        ),
      ],
    );
  }
}

/// Block / risk-flag dialog: closed scope + reason codes (never free text), so
/// the action carries no narrative — the server's value-level guard, surfaced.
class _BlockTargetDialog extends ConsumerStatefulWidget {
  const _BlockTargetDialog({required this.reportId});

  final String reportId;

  @override
  ConsumerState<_BlockTargetDialog> createState() => _BlockTargetDialogState();
}

class _BlockTargetDialogState extends ConsumerState<_BlockTargetDialog> {
  OperatorBlockScope _scope = OperatorBlockScope.reservation;
  OperatorBlockReason _reason = OperatorBlockReason.safetyRisk;
  bool _isRiskFlag = false;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('차단 / 위험 플래그'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          DropdownButtonFormField<OperatorBlockScope>(
            initialValue: _scope,
            decoration: const InputDecoration(labelText: '범위'),
            items: [
              for (final scope in OperatorBlockScope.values)
                DropdownMenuItem<OperatorBlockScope>(
                  value: scope,
                  child: Text(scope.label),
                ),
            ],
            onChanged: (value) => setState(() => _scope = value ?? _scope),
          ),
          DropdownButtonFormField<OperatorBlockReason>(
            initialValue: _reason,
            decoration: const InputDecoration(labelText: '사유'),
            items: [
              for (final reason in OperatorBlockReason.values)
                DropdownMenuItem<OperatorBlockReason>(
                  value: reason,
                  child: Text(reason.label),
                ),
            ],
            onChanged: (value) => setState(() => _reason = value ?? _reason),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('위험 플래그로 처리 (소프트 제한)'),
            value: _isRiskFlag,
            onChanged: (value) => setState(() => _isRiskFlag = value),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: () {
            final messenger = ScaffoldMessenger.of(context);
            ref
                .read(operatorSafetyControllerProvider.notifier)
                .blockUser(
                  reportId: widget.reportId,
                  scope: _scope,
                  reason: _reason,
                  isRiskFlag: _isRiskFlag,
                );
            Navigator.of(context).pop();
            messenger.showSnackBar(
              SnackBar(
                content: Text(_isRiskFlag ? '위험 플래그로 처리했습니다.' : '차단했습니다.'),
              ),
            );
          },
          child: Text(_isRiskFlag ? '위험 플래그' : '차단'),
        ),
      ],
    );
  }
}

AssenBadgeHue _severityHue(OperatorReportSeverity severity) =>
    switch (severity) {
      OperatorReportSeverity.low => AssenBadgeHue.sky,
      OperatorReportSeverity.medium => AssenBadgeHue.lemon,
      OperatorReportSeverity.high => AssenBadgeHue.peach,
      OperatorReportSeverity.critical => AssenBadgeHue.strawberry,
    };

// Status uses a free [AssenBadge] hue (not AssenStatusBadge) because the
// four-state safety lifecycle needs four *calm* hues: AssenStatusBadge's only
// spare kind is `cancelled` (red), and red is reserved for destructive actions
// (tokens.md §1) — it would mis-signal a resolved case as an error.
AssenBadgeHue _statusHue(OperatorReportStatus status) => switch (status) {
  OperatorReportStatus.received => AssenBadgeHue.matcha,
  OperatorReportStatus.reviewing => AssenBadgeHue.sky,
  OperatorReportStatus.actioned => AssenBadgeHue.lemon,
  OperatorReportStatus.closed => AssenBadgeHue.lavender,
};

String _relativeTime(DateTime then) {
  final delta = DateTime.now().difference(then);
  if (delta.inMinutes < 1) return '방금 전';
  if (delta.inHours < 1) return '${delta.inMinutes}분 전';
  if (delta.inDays < 1) return '${delta.inHours}시간 전';
  if (delta.inDays == 1) return '어제';
  return '${delta.inDays}일 전';
}

String _formatDateTime(DateTime time) =>
    '${time.month}월 ${time.day}일 '
    '${time.hour.toString().padLeft(2, '0')}:'
    '${time.minute.toString().padLeft(2, '0')}';
