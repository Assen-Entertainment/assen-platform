import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/schedule/operator_schedule_providers.dart';
import 'package:operator_app/schedule/operator_schedule_repository.dart';
import 'package:ui_kit/ui_kit.dart';

/// F05 operator schedule console (출근표 관리).
///
/// Two views switch via a segmented control: a date-keyed **board** (cast ×
/// shift window with draft/published/unpublished status badges, draft
/// create/edit, publish/unpublish, and change requests against published
/// entries) and the **change log** (the `ScheduleChangeRequest` history with
/// approve/reject for pending rows). Separation of duties is enforced
/// authoritatively by the server; the console additionally disables the
/// self-approval affordance for a change the current operator filed (see
/// [currentOperatorIdProvider]). All routes are operator+, so — unlike the O4
/// safety console — there is no manager tier or PII redaction here.
class OperatorScheduleScreen extends ConsumerStatefulWidget {
  /// Creates the schedule console.
  const OperatorScheduleScreen({super.key});

  @override
  ConsumerState<OperatorScheduleScreen> createState() =>
      _OperatorScheduleScreenState();
}

class _OperatorScheduleScreenState
    extends ConsumerState<OperatorScheduleScreen> {
  int _view = 0;
  DateTime? _selectedDate;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

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
              '출근표 관리',
              style: TextStyle(
                color: colors.ink900,
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: SpacingTokens.s4),
            AssenSegmentedTabs(
              segments: const ['출근표 보드', '변경 로그'],
              selectedIndex: _view,
              onChanged: (index) => setState(() => _view = index),
            ),
            const SizedBox(height: SpacingTokens.s5),
            if (_view == 0)
              _BoardView(
                selectedDate: _selectedDate,
                onSelectDate: (date) => setState(() => _selectedDate = date),
              )
            else
              const _ChangeLogView(),
          ],
        ),
      ),
    );
  }
}

/// The date-keyed board: a date strip + the selected day's entry cards.
class _BoardView extends ConsumerWidget {
  const _BoardView({required this.selectedDate, required this.onSelectDate});

  final DateTime? selectedDate;
  final ValueChanged<DateTime> onSelectDate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final entries = ref.watch(operatorScheduleControllerProvider).entries;

    final dates = _distinctDates(entries);
    if (dates.isEmpty) {
      return _EmptyPanel(colors: colors, message: '등록된 출근표가 없습니다.');
    }
    final active = dates.firstWhere(
      (d) => selectedDate != null && _sameDate(d, selectedDate!),
      orElse: () => dates.first,
    );
    final dayEntries = entries.where((e) => _sameDate(e.workDate, active));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DateStrip(dates: dates, active: active, onSelect: onSelectDate),
        const SizedBox(height: SpacingTokens.s4),
        Row(
          children: [
            Expanded(
              child: Text(
                '${_formatDayHeader(active)} 출근 캐스트',
                style: TextStyle(
                  color: colors.ink900,
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () => _openCreateDraft(context, active),
              icon: const Icon(Icons.add, size: SpacingTokens.s4),
              label: const Text('초안 추가'),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.s2),
        for (final entry in dayEntries) ...[
          _EntryCard(
            entry: entry,
            onTap: () => _openEntryDetail(context, entry.id),
          ),
          const SizedBox(height: SpacingTokens.s3),
        ],
        const SizedBox(height: SpacingTokens.s2),
        const AssenNoticeBar(
          kind: AssenNoticeKind.warning,
          message: '게시본 변경은 다른 운영자의 승인을 거쳐 반영돼요.',
        ),
      ],
    );
  }
}

/// The horizontally scrolling date selector chip row.
class _DateStrip extends StatelessWidget {
  const _DateStrip({
    required this.dates,
    required this.active,
    required this.onSelect,
  });

  final List<DateTime> dates;
  final DateTime active;
  final ValueChanged<DateTime> onSelect;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (var i = 0; i < dates.length; i++) ...[
            AssenFilterChip(
              label: _formatChip(dates[i]),
              selected: _sameDate(dates[i], active),
              onSelected: (_) => onSelect(dates[i]),
            ),
            if (i != dates.length - 1) const SizedBox(width: SpacingTokens.s2),
          ],
        ],
      ),
    );
  }
}

/// A single schedule entry: cast badge, shift window, status, note.
class _EntryCard extends StatelessWidget {
  const _EntryCard({required this.entry, required this.onTap});

  final OperatorScheduleEntry entry;
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
              AssenBadge(label: entry.castId, hue: _castHue(entry.castId)),
              const SizedBox(width: SpacingTokens.s2),
              AssenBadge(
                label: entry.status.label,
                hue: _statusHue(entry.status),
              ),
              const Spacer(),
              Text(
                _shiftWindow(entry),
                style: TextStyle(
                  color: colors.ink900,
                  fontSize: TypographyTokens.bodyMSize,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          if (entry.note.isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.s2),
            Text(
              entry.note,
              style: TextStyle(
                color: colors.ink700,
                fontSize: TypographyTokens.bodySSize,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// The per-entry detail + actions dialog (re-reads the live entry by id).
class _EntryDetailDialog extends ConsumerWidget {
  const _EntryDetailDialog({required this.entryId});

  final String entryId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final entries = ref.watch(operatorScheduleControllerProvider).entries;
    OperatorScheduleEntry? found;
    for (final candidate in entries) {
      if (candidate.id == entryId) {
        found = candidate;
        break;
      }
    }
    if (found == null) {
      return const _MissingDialog(
        title: '출근표',
        message: '항목을 찾을 수 없습니다.',
      );
    }
    final entry = found;
    final controller = ref.read(operatorScheduleControllerProvider.notifier);
    final isDraft = entry.status == ScheduleEntryStatus.draft;
    final isPublished = entry.status == ScheduleEntryStatus.published;
    final isUnpublished = entry.status == ScheduleEntryStatus.unpublished;

    return AlertDialog(
      title: Text('${entry.castId} 출근표'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AssenKeyValueRow(
              label: '근무일',
              value: _formatDayHeader(entry.workDate),
            ),
            AssenKeyValueRow(label: '시간대', value: _shiftWindow(entry)),
            AssenKeyValueRow(label: '상태', value: entry.status.label),
            AssenKeyValueRow(
              label: '메모',
              value: entry.note.isEmpty ? '(없음)' : entry.note,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('닫기'),
        ),
        if (isDraft)
          TextButton(
            onPressed: () => _openEditDraft(context, entryId),
            child: const Text('수정'),
          ),
        if (isPublished)
          TextButton(
            onPressed: () => _openRequestChange(context, entryId),
            child: const Text('변경 요청'),
          ),
        if (isPublished)
          TextButton(
            onPressed: () {
              final messenger = ScaffoldMessenger.of(context);
              controller.unpublishEntry(entryId: entryId);
              Navigator.of(context).pop();
              messenger.showSnackBar(
                const SnackBar(content: Text('비공개로 전환했습니다.')),
              );
            },
            child: const Text('비공개'),
          ),
        if (isDraft || isUnpublished)
          FilledButton(
            onPressed: () {
              final messenger = ScaffoldMessenger.of(context);
              controller.publishEntry(entryId);
              Navigator.of(context).pop();
              messenger.showSnackBar(
                const SnackBar(content: Text('게시했습니다.')),
              );
            },
            child: const Text('게시'),
          ),
      ],
    );
  }
}

/// The change log: a status filter + the change-request history (newest first).
class _ChangeLogView extends ConsumerStatefulWidget {
  const _ChangeLogView();

  @override
  ConsumerState<_ChangeLogView> createState() => _ChangeLogViewState();
}

class _ChangeLogViewState extends ConsumerState<_ChangeLogView> {
  /// null = 전체 (no filter); otherwise the chosen status (enum-limited, so an
  /// invalid value the server would 400 is never representable here).
  ScheduleChangeStatus? _filter;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final currentOperatorId = ref.watch(currentOperatorIdProvider);
    final data = ref.watch(operatorScheduleControllerProvider);
    // The change log only carries entry_id (server `ChangeRequestOut` shape);
    // the cast label is joined from the entries the console already loads.
    final castByEntryId = {for (final e in data.entries) e.id: e.castId};
    final visible = data.changes
        .where((c) => _filter == null || c.status == _filter)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<ScheduleChangeStatus?>(
          initialValue: _filter,
          decoration: const InputDecoration(labelText: '상태 필터'),
          items: [
            const DropdownMenuItem<ScheduleChangeStatus?>(
              child: Text('전체'), // value omitted == null == "no filter"
            ),
            for (final status in ScheduleChangeStatus.values)
              DropdownMenuItem<ScheduleChangeStatus?>(
                value: status,
                child: Text(status.label),
              ),
          ],
          onChanged: (value) => setState(() => _filter = value),
        ),
        const SizedBox(height: SpacingTokens.s4),
        if (visible.isEmpty)
          _EmptyPanel(colors: colors, message: '해당 상태의 변경 요청이 없습니다.')
        else
          for (final change in visible) ...[
            _ChangeCard(
              change: change,
              castLabel: castByEntryId[change.entryId] ?? '출근표',
              currentOperatorId: currentOperatorId,
            ),
            const SizedBox(height: SpacingTokens.s3),
          ],
      ],
    );
  }
}

/// One change-request row: before→after diff, reason, requester/decider, and —
/// for a pending change — approve/reject (자가승인은 비활성).
class _ChangeCard extends ConsumerWidget {
  const _ChangeCard({
    required this.change,
    required this.castLabel,
    required this.currentOperatorId,
  });

  final OperatorScheduleChangeRequest change;
  final String castLabel;
  final int currentOperatorId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final controller = ref.read(operatorScheduleControllerProvider.notifier);
    final isPending = change.status == ScheduleChangeStatus.pending;
    final isOwnRequest = change.requestedById == currentOperatorId;

    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AssenBadge(
                label: change.status.label,
                hue: _changeStatusHue(change.status),
              ),
              const SizedBox(width: SpacingTokens.s2),
              Text(
                '$castLabel 출근표 변경',
                style: TextStyle(
                  color: colors.ink900,
                  fontSize: TypographyTokens.bodyLSize,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const Spacer(),
              Text(
                _relativeTime(change.createdAt),
                style: TextStyle(
                  color: colors.ink500,
                  fontSize: TypographyTokens.bodySSize,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.s3),
          for (final key in change.proposed.keys)
            _DiffRow(
              label: changeableFieldLabel(key),
              before: _displayValue(key, change.before[key] ?? ''),
              after: _displayValue(key, change.proposed[key] ?? ''),
            ),
          if (change.reason.isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.s2),
            Text(
              '사유: ${change.reason}',
              style: TextStyle(
                color: colors.ink700,
                fontSize: TypographyTokens.bodySSize,
              ),
            ),
          ],
          const SizedBox(height: SpacingTokens.s1),
          Text(
            _decisionLine(change),
            style: TextStyle(
              color: colors.ink500,
              fontSize: TypographyTokens.bodySSize,
            ),
          ),
          if (isPending) ...[
            const SizedBox(height: SpacingTokens.s3),
            if (isOwnRequest)
              const AssenNoticeBar(
                message: '본인이 요청한 변경은 다른 운영자가 승인해야 해요.',
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () {
                    final messenger = ScaffoldMessenger.of(context);
                    controller.rejectChange(changeId: change.id);
                    messenger.showSnackBar(
                      const SnackBar(content: Text('변경을 거부했습니다.')),
                    );
                  },
                  child: const Text('거부'),
                ),
                const SizedBox(width: SpacingTokens.s2),
                FilledButton(
                  onPressed: isOwnRequest
                      ? null
                      : () {
                          final messenger = ScaffoldMessenger.of(context);
                          controller.approveChange(changeId: change.id);
                          messenger.showSnackBar(
                            const SnackBar(content: Text('변경을 승인했습니다.')),
                          );
                        },
                  child: const Text('승인'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// A single before→after line in a change card.
class _DiffRow extends StatelessWidget {
  const _DiffRow({
    required this.label,
    required this.before,
    required this.after,
  });

  final String label;
  final String before;
  final String after;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s1),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 56,
            child: Text(
              label,
              style: TextStyle(
                color: colors.ink500,
                fontSize: TypographyTokens.bodySSize,
              ),
            ),
          ),
          Expanded(
            child: Text(
              '$before → $after',
              style: TextStyle(
                color: colors.ink900,
                fontSize: TypographyTokens.bodySSize,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Shared empty-state panel.
class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.colors, required this.message});

  final AssenColors colors;
  final String message;

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
        message,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: colors.ink700,
          fontSize: TypographyTokens.bodyMSize,
        ),
      ),
    );
  }
}

/// AlertDialog shown when an entry/change id no longer resolves.
class _MissingDialog extends StatelessWidget {
  const _MissingDialog({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('닫기'),
        ),
      ],
    );
  }
}

/// Create-draft form: cast id, shift window (HH:MM), optional note. The new
/// entry lands as a draft on the board's selected [date].
class _CreateDraftDialog extends ConsumerStatefulWidget {
  const _CreateDraftDialog({required this.date});

  final DateTime date;

  @override
  ConsumerState<_CreateDraftDialog> createState() => _CreateDraftDialogState();
}

class _CreateDraftDialogState extends ConsumerState<_CreateDraftDialog> {
  final _castController = TextEditingController();
  final _startController = TextEditingController(text: '12:00');
  final _endController = TextEditingController(text: '18:00');
  final _noteController = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _castController.dispose();
    _startController.dispose();
    _endController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  void _submit() {
    final cast = _castController.text.trim();
    final start = tryParseScheduleTime(_startController.text);
    final end = tryParseScheduleTime(_endController.text);
    if (cast.isEmpty) {
      setState(() => _error = '캐스트를 입력하세요.');
      return;
    }
    if (start == null || end == null) {
      setState(() => _error = '시간 형식은 HH:MM이어야 합니다.');
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    ref
        .read(operatorScheduleControllerProvider.notifier)
        .createDraft(
          workDate: widget.date,
          castId: cast,
          startTime: start,
          endTime: end,
          note: _noteController.text.trim(),
        );
    Navigator.of(context).pop();
    messenger.showSnackBar(
      const SnackBar(content: Text('초안을 추가했습니다.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('출근표 초안 추가'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _castController,
              decoration: const InputDecoration(labelText: '캐스트'),
            ),
            TextField(
              controller: _startController,
              decoration: const InputDecoration(labelText: '시작 (HH:MM)'),
            ),
            TextField(
              controller: _endController,
              decoration: const InputDecoration(labelText: '종료 (HH:MM)'),
            ),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(labelText: '메모 (선택)'),
            ),
            if (_error != null) _ErrorText(message: _error!),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(onPressed: _submit, child: const Text('추가')),
      ],
    );
  }
}

/// Edit-draft form (draft entries only): adjust shift window / note directly.
class _EditDraftDialog extends ConsumerStatefulWidget {
  const _EditDraftDialog({required this.entryId});

  final String entryId;

  @override
  ConsumerState<_EditDraftDialog> createState() => _EditDraftDialogState();
}

class _EditDraftDialogState extends ConsumerState<_EditDraftDialog> {
  late final TextEditingController _startController;
  late final TextEditingController _endController;
  late final TextEditingController _noteController;
  String? _error;

  @override
  void initState() {
    super.initState();
    final entry = _currentEntry();
    _startController = TextEditingController(
      text: entry == null ? '' : formatScheduleTimeShort(entry.startTime),
    );
    _endController = TextEditingController(
      text: entry == null ? '' : formatScheduleTimeShort(entry.endTime),
    );
    _noteController = TextEditingController(text: entry?.note ?? '');
  }

  OperatorScheduleEntry? _currentEntry() {
    final entries = ref.read(operatorScheduleControllerProvider).entries;
    for (final entry in entries) {
      if (entry.id == widget.entryId) return entry;
    }
    return null;
  }

  @override
  void dispose() {
    _startController.dispose();
    _endController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  void _submit() {
    final start = tryParseScheduleTime(_startController.text);
    final end = tryParseScheduleTime(_endController.text);
    if (start == null || end == null) {
      setState(() => _error = '시간 형식은 HH:MM이어야 합니다.');
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    ref
        .read(operatorScheduleControllerProvider.notifier)
        .editDraft(
          entryId: widget.entryId,
          startTime: start,
          endTime: end,
          note: _noteController.text.trim(),
        );
    Navigator.of(context).pop();
    messenger.showSnackBar(
      const SnackBar(content: Text('초안을 수정했습니다.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('초안 수정'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _startController,
              decoration: const InputDecoration(labelText: '시작 (HH:MM)'),
            ),
            TextField(
              controller: _endController,
              decoration: const InputDecoration(labelText: '종료 (HH:MM)'),
            ),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(labelText: '메모 (선택)'),
            ),
            if (_error != null) _ErrorText(message: _error!),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(onPressed: _submit, child: const Text('저장')),
      ],
    );
  }
}

/// Request-change form (published entries): proposes a new shift window / note
/// plus a reason. Only changed fields become the proposed override; an empty
/// change is rejected so the pending list never carries a no-op.
class _RequestChangeDialog extends ConsumerStatefulWidget {
  const _RequestChangeDialog({required this.entryId});

  final String entryId;

  @override
  ConsumerState<_RequestChangeDialog> createState() =>
      _RequestChangeDialogState();
}

class _RequestChangeDialogState extends ConsumerState<_RequestChangeDialog> {
  late final TextEditingController _startController;
  late final TextEditingController _endController;
  late final TextEditingController _noteController;
  late final TimeOfDay? _originalStart;
  late final TimeOfDay? _originalEnd;
  late final String _originalNote;
  final _reasonController = TextEditingController();
  String? _error;

  @override
  void initState() {
    super.initState();
    final entry = _currentEntry();
    _originalStart = entry?.startTime;
    _originalEnd = entry?.endTime;
    _originalNote = entry?.note ?? '';
    _startController = TextEditingController(
      text: entry == null ? '' : formatScheduleTimeShort(entry.startTime),
    );
    _endController = TextEditingController(
      text: entry == null ? '' : formatScheduleTimeShort(entry.endTime),
    );
    _noteController = TextEditingController(text: _originalNote);
  }

  OperatorScheduleEntry? _currentEntry() {
    final entries = ref.read(operatorScheduleControllerProvider).entries;
    for (final entry in entries) {
      if (entry.id == widget.entryId) return entry;
    }
    return null;
  }

  @override
  void dispose() {
    _startController.dispose();
    _endController.dispose();
    _noteController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  void _submit() {
    final start = tryParseScheduleTime(_startController.text);
    final end = tryParseScheduleTime(_endController.text);
    if (start == null || end == null) {
      setState(() => _error = '시간 형식은 HH:MM이어야 합니다.');
      return;
    }
    final proposed = <String, String>{};
    if (_originalStart == null || start != _originalStart) {
      proposed['start_time'] = formatScheduleTime(start);
    }
    if (_originalEnd == null || end != _originalEnd) {
      proposed['end_time'] = formatScheduleTime(end);
    }
    final note = _noteController.text.trim();
    if (note != _originalNote) {
      proposed['note'] = note;
    }
    if (proposed.isEmpty) {
      setState(() => _error = '변경된 내용이 없습니다.');
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    ref
        .read(operatorScheduleControllerProvider.notifier)
        .requestChange(
          entryId: widget.entryId,
          proposed: proposed,
          reason: _reasonController.text.trim(),
        );
    Navigator.of(context).pop();
    messenger.showSnackBar(
      const SnackBar(content: Text('변경 요청을 제출했습니다.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('게시본 변경 요청'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _startController,
              decoration: const InputDecoration(labelText: '시작 (HH:MM)'),
            ),
            TextField(
              controller: _endController,
              decoration: const InputDecoration(labelText: '종료 (HH:MM)'),
            ),
            TextField(
              controller: _noteController,
              decoration: const InputDecoration(labelText: '메모'),
            ),
            TextField(
              controller: _reasonController,
              decoration: const InputDecoration(labelText: '사유 (선택)'),
            ),
            if (_error != null) _ErrorText(message: _error!),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(onPressed: _submit, child: const Text('변경 요청')),
      ],
    );
  }
}

/// Inline form-error text (rose ink).
class _ErrorText extends StatelessWidget {
  const _ErrorText({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Padding(
      padding: const EdgeInsets.only(top: SpacingTokens.s2),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Text(
          message,
          style: TextStyle(
            color: colors.roseMain,
            fontSize: TypographyTokens.bodySSize,
          ),
        ),
      ),
    );
  }
}

Future<void> _openEntryDetail(BuildContext context, String entryId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _EntryDetailDialog(entryId: entryId),
  );
}

Future<void> _openCreateDraft(BuildContext context, DateTime date) {
  return showDialog<void>(
    context: context,
    builder: (_) => _CreateDraftDialog(date: date),
  );
}

Future<void> _openEditDraft(BuildContext context, String entryId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _EditDraftDialog(entryId: entryId),
  );
}

Future<void> _openRequestChange(BuildContext context, String entryId) {
  return showDialog<void>(
    context: context,
    builder: (_) => _RequestChangeDialog(entryId: entryId),
  );
}

/// The distinct work dates present in [entries], ascending.
List<DateTime> _distinctDates(List<OperatorScheduleEntry> entries) {
  final seen = <String>{};
  final dates = <DateTime>[];
  for (final entry in entries) {
    final key = formatScheduleDate(entry.workDate);
    if (seen.add(key)) dates.add(entry.workDate);
  }
  dates.sort();
  return dates;
}

bool _sameDate(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;

String _shiftWindow(OperatorScheduleEntry entry) =>
    '${formatScheduleTimeShort(entry.startTime)}'
    '–${formatScheduleTimeShort(entry.endTime)}';

/// Renders a before/after raw value for display (times trimmed to HH:MM, an
/// empty note shown as a placeholder).
String _displayValue(String key, String raw) {
  if (key == 'note') return raw.isEmpty ? '(없음)' : raw;
  if (key == 'start_time' || key == 'end_time') {
    final parts = raw.split(':');
    if (parts.length >= 2) return '${parts[0]}:${parts[1]}';
  }
  return raw;
}

const List<String> _weekdayLabels = ['월', '화', '수', '목', '금', '토', '일'];

String _formatChip(DateTime date) {
  // DateTime.weekday is 1–7 (Mon–Sun), so weekday-1 indexes 0–6.
  final weekday = _weekdayLabels[date.weekday - 1];
  return '${date.month}/${date.day} ($weekday)';
}

String _formatDayHeader(DateTime date) {
  final weekday = _weekdayLabels[date.weekday - 1];
  return '${date.month}월 ${date.day}일 ($weekday)';
}

String _decisionLine(OperatorScheduleChangeRequest change) {
  final requester = '요청: 운영자 #${change.requestedById}';
  if (change.status == ScheduleChangeStatus.pending) {
    return requester;
  }
  final decider = change.decidedById == null
      ? ''
      : ' · 결정: 운영자 #${change.decidedById}';
  final note = change.decisionNote.isEmpty ? '' : ' · ${change.decisionNote}';
  return '$requester$decider$note';
}

String _relativeTime(DateTime then) {
  final delta = DateTime.now().difference(then);
  if (delta.inMinutes < 1) return '방금 전';
  if (delta.inHours < 1) return '${delta.inMinutes}분 전';
  if (delta.inDays < 1) return '${delta.inHours}시간 전';
  if (delta.inDays == 1) return '어제';
  return '${delta.inDays}일 전';
}

const Map<String, AssenBadgeHue> _castHues = {
  '미오': AssenBadgeHue.strawberry,
  '유키': AssenBadgeHue.sky,
  '모카': AssenBadgeHue.peach,
  '베리': AssenBadgeHue.lavender,
};

AssenBadgeHue _castHue(String castId) =>
    _castHues[castId] ?? AssenBadgeHue.matcha;

AssenBadgeHue _statusHue(ScheduleEntryStatus status) => switch (status) {
  ScheduleEntryStatus.draft => AssenBadgeHue.lemon,
  ScheduleEntryStatus.published => AssenBadgeHue.matcha,
  ScheduleEntryStatus.unpublished => AssenBadgeHue.lavender,
};

// The change lifecycle uses calm [AssenBadge] hues (not a red 'cancelled'
// status): red is reserved for destructive actions (tokens.md §1), so a
// rejected change reads as a neutral terminal state, not an error.
AssenBadgeHue _changeStatusHue(ScheduleChangeStatus status) => switch (status) {
  ScheduleChangeStatus.pending => AssenBadgeHue.lemon,
  ScheduleChangeStatus.approved => AssenBadgeHue.matcha,
  ScheduleChangeStatus.rejected => AssenBadgeHue.lavender,
};
