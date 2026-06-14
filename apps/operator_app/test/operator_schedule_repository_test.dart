import 'package:flutter/material.dart' show TimeOfDay;
import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/schedule/operator_schedule_repository.dart';

/// Direct repository tests for the fail-closed guards that mirror the ASS-93
/// server (`server/apps/schedule/services.py`). These are exercised without the
/// UI so a refactor that removes a guard is caught even if every widget keeps
/// gating the affordance — the authoritative parity the doc comments stress.
void main() {
  InMemoryOperatorScheduleRepository repo() =>
      InMemoryOperatorScheduleRepository(now: DateTime(2026, 6, 14, 10));

  group('edit_draft parity', () {
    test('editing a published entry throws (draft-only)', () {
      // entry-1 is seeded published.
      expect(
        () => repo().editDraft(
          entryId: 'entry-1',
          startTime: const TimeOfDay(hour: 9, minute: 0),
        ),
        throwsStateError,
      );
    });

    test('editing a draft entry succeeds', () {
      // entry-2 is seeded draft.
      final updated = repo().editDraft(
        entryId: 'entry-2',
        endTime: const TimeOfDay(hour: 21, minute: 0),
      );
      expect(updated.status, ScheduleEntryStatus.draft);
      expect(updated.endTime, const TimeOfDay(hour: 21, minute: 0));
    });
  });

  group('request_change parity', () {
    test('a change against a draft entry throws (published-only)', () {
      expect(
        () => repo().requestChange(
          entryId: 'entry-2',
          proposed: const {'note': 'x'},
          requestedById: 1,
        ),
        throwsStateError,
      );
    });

    test('an unchangeable field key is rejected (FormatException)', () {
      expect(
        () => repo().requestChange(
          entryId: 'entry-1',
          proposed: const {'cast_id': 'someone'},
          requestedById: 1,
        ),
        throwsFormatException,
      );
    });

    test('a change against a published entry is filed pending', () {
      final change = repo().requestChange(
        entryId: 'entry-1',
        proposed: const {'start_time': '13:00:00'},
        requestedById: 1,
        reason: 'shift',
      );
      expect(change.status, ScheduleChangeStatus.pending);
      expect(change.before['start_time'], '12:00:00');
    });

    test('the change is stamped with the requesting operator, so that '
        'operator cannot then self-approve it', () {
      final r = repo();
      // Operator #2 files a change against the published entry-1...
      final change = r.requestChange(
        entryId: 'entry-1',
        proposed: const {'note': 'shift'},
        requestedById: 2,
      );
      expect(change.requestedById, 2);
      // ...and #2 cannot approve their own request (SoD holds for any actor,
      // not just the seeded #1 — this is the Codex HIGH fix).
      expect(
        () => r.approveChange(changeId: change.id, actorId: 2),
        throwsStateError,
      );
    });
  });

  group('approve_change separation of duties', () {
    test('self-approval throws even though the UI also disables it', () {
      // change-2 is seeded with requestedById == 1.
      expect(
        () => repo().approveChange(changeId: 'change-2', actorId: 1),
        throwsStateError,
      );
    });

    test('approving as a different operator applies the change', () {
      final r = repo();
      // change-1 was filed by operator #2; #1 may approve it.
      final decided = r.approveChange(changeId: 'change-1', actorId: 1);
      expect(decided.status, ScheduleChangeStatus.approved);
      expect(decided.decidedById, 1);
      // The proposed window is applied to entry-1.
      final entry = r.listEntries().firstWhere((e) => e.id == 'entry-1');
      expect(entry.startTime, const TimeOfDay(hour: 13, minute: 0));
      expect(entry.endTime, const TimeOfDay(hour: 19, minute: 0));
    });

    test('approving an already-decided change throws (pending-only)', () {
      final r = repo()..approveChange(changeId: 'change-1', actorId: 1);
      expect(
        () => r.approveChange(changeId: 'change-1', actorId: 2),
        throwsStateError,
      );
    });
  });

  group('reject_change', () {
    test('self-rejection is allowed (matches server: no SoD on reject)', () {
      // change-2 was filed by #1; #1 may still reject it (server parity).
      final decided = repo().rejectChange(changeId: 'change-2', actorId: 1);
      expect(decided.status, ScheduleChangeStatus.rejected);
      expect(decided.decidedById, 1);
    });
  });

  group('listChanges enum filter', () {
    test('filters to a single status', () {
      final approved = repo().listChanges(
        status: ScheduleChangeStatus.approved,
      );
      expect(approved, hasLength(1)); // only seeded change-3
      expect(approved.single.id, 'change-3');
    });

    test('no filter returns every change, newest first', () {
      final all = repo().listChanges();
      expect(all, hasLength(3));
      // change-2 (now-2h) is newest, then change-1 (now-3h), then change-3.
      expect(all.first.id, 'change-2');
    });
  });

  test('an unknown id raises a controlled StateError (no RangeError)', () {
    expect(() => repo().publishEntry('nope'), throwsStateError);
    expect(
      () => repo().approveChange(changeId: 'nope', actorId: 1),
      throwsStateError,
    );
  });

  group('strict ISO parsing mirrors the server', () {
    test('parseScheduleTime rejects out-of-range or unpadded input', () {
      // time.fromisoformat would reject all of these — we must not accept.
      expect(() => parseScheduleTime('12:30:99'), throwsFormatException);
      expect(() => parseScheduleTime('24:00'), throwsFormatException);
      expect(() => parseScheduleTime('1:02'), throwsFormatException);
      expect(() => parseScheduleTime('01:2'), throwsFormatException);
      // A valid seconds value parses (and is dropped by TimeOfDay).
      expect(
        parseScheduleTime('13:00:30'),
        const TimeOfDay(hour: 13, minute: 0),
      );
    });

    test('parseScheduleDate rejects datetime/unpadded/overflow input', () {
      expect(
        () => parseScheduleDate('2026-06-14T10:00'),
        throwsFormatException,
      );
      expect(() => parseScheduleDate('2026-6-4'), throwsFormatException);
      // Calendar overflow that DateTime would silently normalise.
      expect(() => parseScheduleDate('2026-02-31'), throwsFormatException);
      expect(() => parseScheduleDate('2026-04-31'), throwsFormatException);
      // Year 0 is below the server's MINYEAR.
      expect(() => parseScheduleDate('0000-01-01'), throwsFormatException);
      expect(parseScheduleDate('2026-06-14'), DateTime(2026, 6, 14));
    });
  });
}
