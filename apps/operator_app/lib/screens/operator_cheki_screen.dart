import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/cheki/operator_cheki_providers.dart';
import 'package:operator_app/cheki/operator_cheki_repository.dart';
import 'package:ui_kit/ui_kit.dart';

/// O3 operator cheki-record screen for manual cheki entry.
class OperatorChekiScreen extends ConsumerWidget {
  /// Creates the cheki record screen.
  const OperatorChekiScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final records = ref.watch(operatorChekiControllerProvider);

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: const AssenAppBar(title: '하츠코이'),
      bottomNavigationBar: AssenBottomCta(
        primaryLabel: '체키 기록',
        onPrimary: () => _showRecordDialog(context),
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
              '체키 기록',
              style: TextStyle(
                color: colors.ink900,
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: SpacingTokens.s5),
            if (records.isEmpty)
              _EmptyChekiList(colors: colors)
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
                    for (final (index, record) in records.indexed) ...[
                      _ChekiRow(
                        record: record,
                        onEdit: () => _showEditDialog(context, record),
                        onVoid: record.status == OperatorChekiStatus.voided
                            ? null
                            : () => _showVoidDialog(context, record),
                      ),
                      if (index != records.length - 1)
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

class _ChekiRow extends StatelessWidget {
  const _ChekiRow({
    required this.record,
    required this.onEdit,
    required this.onVoid,
  });

  final OperatorChekiRecord record;
  final VoidCallback onEdit;
  final VoidCallback? onVoid;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final voided = record.status == OperatorChekiStatus.voided;
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
          Expanded(
            child: Text(
              '${record.castName} · ${record.chekiType} ×${record.quantity}',
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
            label: voided ? '무효' : '기록',
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

class _EmptyChekiList extends StatelessWidget {
  const _EmptyChekiList({required this.colors});

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
        '오늘 체키 기록이 없습니다.',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: colors.ink700,
          fontSize: TypographyTokens.bodyMSize,
        ),
      ),
    );
  }
}

// Dialogs own their controllers via ConsumerStatefulWidget so disposing after
// the close transition is safe (see operator_checkin_screen.dart rationale).

Future<void> _showRecordDialog(BuildContext context) {
  return showDialog<void>(
    context: context,
    builder: (_) => const _RecordChekiDialog(),
  );
}

Future<void> _showEditDialog(BuildContext context, OperatorChekiRecord record) {
  return showDialog<void>(
    context: context,
    builder: (_) => _EditChekiDialog(record: record),
  );
}

Future<void> _showVoidDialog(BuildContext context, OperatorChekiRecord record) {
  return showDialog<void>(
    context: context,
    builder: (_) => _VoidChekiDialog(record: record),
  );
}

class _RecordChekiDialog extends ConsumerStatefulWidget {
  const _RecordChekiDialog();

  @override
  ConsumerState<_RecordChekiDialog> createState() => _RecordChekiDialogState();
}

class _RecordChekiDialogState extends ConsumerState<_RecordChekiDialog> {
  late String _castId;
  late String _chekiType;
  final _quantityController = TextEditingController(text: '1');

  @override
  void initState() {
    super.initState();
    final controller = ref.read(operatorChekiControllerProvider.notifier);
    _castId = controller.castOptions.first.id;
    _chekiType = controller.chekiTypes.first;
  }

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = ref.read(operatorChekiControllerProvider.notifier);
    return AlertDialog(
      title: const Text('체키 기록'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          DropdownButtonFormField<String>(
            initialValue: _castId,
            decoration: const InputDecoration(labelText: '캐스트'),
            items: [
              for (final cast in controller.castOptions)
                DropdownMenuItem<String>(
                  value: cast.id,
                  child: Text(cast.name),
                ),
            ],
            onChanged: (value) => setState(() => _castId = value ?? _castId),
          ),
          DropdownButtonFormField<String>(
            initialValue: _chekiType,
            decoration: const InputDecoration(labelText: '종류'),
            items: [
              for (final type in controller.chekiTypes)
                DropdownMenuItem<String>(value: type, child: Text(type)),
            ],
            onChanged: (value) =>
                setState(() => _chekiType = value ?? _chekiType),
          ),
          TextField(
            controller: _quantityController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '수량'),
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
            final quantity = int.tryParse(_quantityController.text.trim()) ?? 1;
            controller.recordCheki(
              castId: _castId,
              chekiType: _chekiType,
              quantity: quantity < 1 ? 1 : quantity,
            );
            Navigator.of(context).pop();
          },
          child: const Text('추가'),
        ),
      ],
    );
  }
}

class _EditChekiDialog extends ConsumerStatefulWidget {
  const _EditChekiDialog({required this.record});

  final OperatorChekiRecord record;

  @override
  ConsumerState<_EditChekiDialog> createState() => _EditChekiDialogState();
}

class _EditChekiDialogState extends ConsumerState<_EditChekiDialog> {
  late final TextEditingController _quantityController = TextEditingController(
    text: '${widget.record.quantity}',
  );

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('체키 수정'),
      content: TextField(
        controller: _quantityController,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(labelText: '수량'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: () {
            final quantity = int.tryParse(_quantityController.text.trim());
            if (quantity == null || quantity < 1) return;
            ref
                .read(operatorChekiControllerProvider.notifier)
                .correctCheki(recordId: widget.record.id, quantity: quantity);
            Navigator.of(context).pop();
          },
          child: const Text('저장'),
        ),
      ],
    );
  }
}

class _VoidChekiDialog extends ConsumerStatefulWidget {
  const _VoidChekiDialog({required this.record});

  final OperatorChekiRecord record;

  @override
  ConsumerState<_VoidChekiDialog> createState() => _VoidChekiDialogState();
}

class _VoidChekiDialogState extends ConsumerState<_VoidChekiDialog> {
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('체키 무효'),
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
                .read(operatorChekiControllerProvider.notifier)
                .voidCheki(recordId: widget.record.id, reason: reason);
            Navigator.of(context).pop();
          },
          child: const Text('무효'),
        ),
      ],
    );
  }
}
