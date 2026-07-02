import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart' show TimeOfDay;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/schedule/operator_schedule_repository.dart';

/// Repository provider for operator schedule data.
final Provider<OperatorScheduleRepository> operatorScheduleRepositoryProvider =
    Provider<OperatorScheduleRepository>(
      (ref) => InMemoryOperatorScheduleRepository(),
    );

/// The current operator's account id — the separation-of-duties surface seam.
///
/// The server is the authoritative enforcer of separation of duties (a change
/// must be approved by a *different* operator), so this is only the UI's local
/// notion of "me" used to *disable* the self-approval affordance. Real identity
/// arrives with the auth token (operator_router P3b); until then the console
/// assumes the default mock operator (#1). Tests override it to exercise both
/// the self (approval disabled) and other (approval enabled) cases.
final Provider<int> currentOperatorIdProvider = Provider<int>((ref) => 1);

/// The board's entries and the change-log rows, refreshed together after every
/// mutation so both views stay consistent.
@immutable
class OperatorScheduleData {
  /// Creates the combined console state.
  const OperatorScheduleData({required this.entries, required this.changes});

  /// All schedule entries (every status), date/time ordered.
  final List<OperatorScheduleEntry> entries;

  /// All change-log rows, newest first.
  final List<OperatorScheduleChangeRequest> changes;
}

/// Controller provider for the operator schedule console.
final operatorScheduleControllerProvider =
    NotifierProvider<OperatorScheduleController, OperatorScheduleData>(
      OperatorScheduleController.new,
    );

/// Riverpod 3 controller that keeps the board and change log fresh after each
/// action against the [OperatorScheduleRepository].
class OperatorScheduleController extends Notifier<OperatorScheduleData> {
  OperatorScheduleRepository get _repo =>
      ref.read(operatorScheduleRepositoryProvider);

  @override
  OperatorScheduleData build() => _read();

  /// Creates a draft entry for [workDate] and refreshes the board.
  void createDraft({
    required DateTime workDate,
    required String castId,
    required TimeOfDay startTime,
    required TimeOfDay endTime,
    String note = '',
  }) {
    _repo.createDraft(
      workDate: workDate,
      castId: castId,
      startTime: startTime,
      endTime: endTime,
      note: note,
    );
    _refresh();
  }

  /// Edits a draft entry directly (no-op surfacing handled by the repo guard).
  void editDraft({
    required String entryId,
    TimeOfDay? startTime,
    TimeOfDay? endTime,
    String? note,
  }) {
    _repo.editDraft(
      entryId: entryId,
      startTime: startTime,
      endTime: endTime,
      note: note,
    );
    _refresh();
  }

  /// Publishes a draft/unpublished entry.
  void publishEntry(String entryId) {
    _repo.publishEntry(entryId);
    _refresh();
  }

  /// Hides a published entry from fans (비공개).
  void unpublishEntry({required String entryId, String reason = ''}) {
    _repo.unpublishEntry(entryId: entryId, reason: reason);
    _refresh();
  }

  /// Files a pending change against a published entry, stamped with the current
  /// operator so the separation-of-duties check has a truthful requester.
  void requestChange({
    required String entryId,
    required Map<String, String> proposed,
    String reason = '',
  }) {
    _repo.requestChange(
      entryId: entryId,
      proposed: proposed,
      requestedById: ref.read(currentOperatorIdProvider),
      reason: reason,
    );
    _refresh();
  }

  /// Approves a pending change as the current operator.
  ///
  /// The repository raises [StateError] on a self-approval; the UI disables
  /// that affordance, but this stays the authoritative guard if bypassed.
  void approveChange({required String changeId, String decisionNote = ''}) {
    _repo.approveChange(
      changeId: changeId,
      actorId: ref.read(currentOperatorIdProvider),
      decisionNote: decisionNote,
    );
    _refresh();
  }

  /// Rejects a pending change as the current operator.
  void rejectChange({required String changeId, String decisionNote = ''}) {
    _repo.rejectChange(
      changeId: changeId,
      actorId: ref.read(currentOperatorIdProvider),
      decisionNote: decisionNote,
    );
    _refresh();
  }

  OperatorScheduleData _read() => OperatorScheduleData(
    entries: _repo.listEntries(),
    changes: _repo.listChanges(),
  );

  void _refresh() => state = _read();
}
