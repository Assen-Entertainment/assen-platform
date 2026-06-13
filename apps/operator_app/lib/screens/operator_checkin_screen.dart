import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/visits/operator_visit_providers.dart';
import 'package:operator_app/visits/operator_visit_repository.dart';
import 'package:ui_kit/ui_kit.dart';

/// O2 operator check-in screen for manual visit records.
class OperatorCheckinScreen extends ConsumerWidget {
  /// Creates the check-in screen.
  const OperatorCheckinScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final visits = ref.watch(operatorVisitControllerProvider);
    final controller = ref.watch(operatorVisitControllerProvider.notifier);

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '하츠코이'),
      bottomNavigationBar: AssenBottomCta(
        primaryLabel: '수동 체크인',
        onPrimary: () => _showManualCheckinDialog(context),
      ),
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
              '체크인',
              style: TextStyle(
                color: colors.ink900,
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: SpacingTokens.s1),
            Text(
              _formatDate(controller.selectedDate),
              style: TextStyle(
                color: colors.ink700,
                fontSize: TypographyTokens.bodyMSize,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: SpacingTokens.s5),
            if (visits.isEmpty)
              _EmptyVisitList(colors: colors)
            else
              DecoratedBox(
                decoration: BoxDecoration(
                  color: colors.white,
                  border: Border.all(color: colors.ink100),
                  borderRadius: const BorderRadius.all(
                    Radius.circular(RadiusTokens.sm),
                  ),
                ),
                child: Column(
                  children: [
                    for (final (index, visit) in visits.indexed) ...[
                      _VisitRow(
                        visit: visit,
                        onEdit: () => _showEditDialog(context, visit),
                        onVoid: visit.status == OperatorVisitStatus.voided
                            ? null
                            : () => _showVoidDialog(context, visit),
                      ),
                      if (index != visits.length - 1)
                        Divider(height: 1, color: colors.ink100),
                    ],
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _VisitRow extends StatelessWidget {
  const _VisitRow({
    required this.visit,
    required this.onEdit,
    required this.onVoid,
  });

  final OperatorVisitRecord visit;
  final VoidCallback onEdit;
  final VoidCallback? onVoid;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final voided = visit.status == OperatorVisitStatus.voided;
    final textColor = voided ? colors.ink500 : colors.ink900;
    final decoration = voided
        ? TextDecoration.lineThrough
        : TextDecoration.none;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s4,
        vertical: SpacingTokens.s3,
      ),
      child: Row(
        children: [
          SizedBox(
            width: SpacingTokens.s12,
            child: Text(
              _formatTime(visit.visitedAt),
              style: TextStyle(
                color: textColor,
                fontSize: TypographyTokens.bodyMSize,
                fontWeight: FontWeight.w700,
                decoration: decoration,
              ),
            ),
          ),
          Expanded(
            child: Text(
              visit.fanNickname,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: textColor,
                fontSize: TypographyTokens.bodyLSize,
                fontWeight: FontWeight.w700,
                decoration: decoration,
              ),
            ),
          ),
          AssenStatusBadge(
            kind: voided ? AssenStatusKind.cancelled : AssenStatusKind.done,
            label: voided ? '무효' : '방문',
          ),
          IconButton(
            tooltip: '수정',
            icon: const Icon(Icons.edit_outlined),
            onPressed: onEdit,
          ),
          IconButton(
            tooltip: '무효',
            icon: const Icon(Icons.block_outlined),
            onPressed: onVoid,
          ),
        ],
      ),
    );
  }
}

class _EmptyVisitList extends StatelessWidget {
  const _EmptyVisitList({required this.colors});

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
        '오늘 방문 기록이 없습니다.',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: colors.ink700,
          fontSize: TypographyTokens.bodyMSize,
        ),
      ),
    );
  }
}

// The dialogs below are ConsumerStatefulWidgets that own their
// TextEditingControllers and dispose them in State.dispose(). Disposing a
// controller right after `await showDialog` crashes ("used after being
// disposed") because the dialog's exit transition still rebuilds the TextField;
// State.dispose() runs only after the widget fully unmounts, which is safe.

Future<void> _showManualCheckinDialog(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (_) => const _ManualCheckinDialog(),
  );
}

Future<void> _showEditDialog(BuildContext context, OperatorVisitRecord visit) {
  return showDialog<void>(
    context: context,
    builder: (_) => _EditVisitDialog(visit: visit),
  );
}

Future<void> _showVoidDialog(BuildContext context, OperatorVisitRecord visit) {
  return showDialog<void>(
    context: context,
    builder: (_) => _VoidVisitDialog(visit: visit),
  );
}

class _ManualCheckinDialog extends ConsumerStatefulWidget {
  const _ManualCheckinDialog();

  @override
  ConsumerState<_ManualCheckinDialog> createState() =>
      _ManualCheckinDialogState();
}

class _ManualCheckinDialogState extends ConsumerState<_ManualCheckinDialog> {
  final _noteController = TextEditingController();
  late String _selectedFanId;

  @override
  void initState() {
    super.initState();
    // ref.read in initState is the Riverpod-sanctioned way to seed state; a
    // field initializer would touch ref before the element is attached.
    _selectedFanId = ref
        .read(operatorVisitControllerProvider.notifier)
        .fanOptions
        .first
        .id;
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = ref.read(operatorVisitControllerProvider.notifier);
    final fans = controller.fanOptions;
    return AlertDialog(
      title: const Text('수동 체크인'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          DropdownButtonFormField<String>(
            initialValue: _selectedFanId,
            decoration: const InputDecoration(labelText: '닉네임'),
            items: [
              for (final fan in fans)
                DropdownMenuItem<String>(
                  value: fan.id,
                  child: Text(fan.nickname),
                ),
            ],
            onChanged: (value) =>
                setState(() => _selectedFanId = value ?? _selectedFanId),
          ),
          TextField(
            controller: _noteController,
            decoration: const InputDecoration(labelText: '메모'),
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
            controller.recordManualVisit(
              fanId: _selectedFanId,
              note: _noteController.text,
            );
            Navigator.of(context).pop();
          },
          child: const Text('추가'),
        ),
      ],
    );
  }
}

class _EditVisitDialog extends ConsumerStatefulWidget {
  const _EditVisitDialog({required this.visit});

  final OperatorVisitRecord visit;

  @override
  ConsumerState<_EditVisitDialog> createState() => _EditVisitDialogState();
}

class _EditVisitDialogState extends ConsumerState<_EditVisitDialog> {
  late final TextEditingController _noteController = TextEditingController(
    text: widget.visit.note,
  );

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('방문 수정'),
      content: TextField(
        controller: _noteController,
        decoration: const InputDecoration(labelText: '메모'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: () {
            ref
                .read(operatorVisitControllerProvider.notifier)
                .correctVisit(
                  recordId: widget.visit.id,
                  note: _noteController.text,
                );
            Navigator.of(context).pop();
          },
          child: const Text('저장'),
        ),
      ],
    );
  }
}

class _VoidVisitDialog extends ConsumerStatefulWidget {
  const _VoidVisitDialog({required this.visit});

  final OperatorVisitRecord visit;

  @override
  ConsumerState<_VoidVisitDialog> createState() => _VoidVisitDialogState();
}

class _VoidVisitDialogState extends ConsumerState<_VoidVisitDialog> {
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('방문 무효'),
      content: TextField(
        controller: _reasonController,
        decoration: const InputDecoration(labelText: '사유'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: () {
            final reason = _reasonController.text.trim();
            if (reason.isEmpty) return;
            ref
                .read(operatorVisitControllerProvider.notifier)
                .voidVisit(recordId: widget.visit.id, reason: reason);
            Navigator.of(context).pop();
          },
          child: const Text('무효'),
        ),
      ],
    );
  }
}

String _formatDate(DateTime date) =>
    '${date.year}년 ${date.month}월 ${date.day}일';

String _formatTime(DateTime time) =>
    '${time.hour.toString().padLeft(2, '0')}:'
    '${time.minute.toString().padLeft(2, '0')}';
