import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/visits/operator_visit_repository.dart';

/// Repository provider for operator visit data.
final Provider<OperatorVisitRepository> operatorVisitRepositoryProvider =
    Provider<OperatorVisitRepository>(
      (ref) => InMemoryOperatorVisitRepository(),
    );

/// Controller provider for the O2 check-in screen.
final operatorVisitControllerProvider =
    NotifierProvider<OperatorVisitController, List<OperatorVisitRecord>>(
      OperatorVisitController.new,
    );

/// Riverpod 3 controller that keeps the current business-day visit list fresh.
class OperatorVisitController extends Notifier<List<OperatorVisitRecord>> {
  late DateTime _selectedDate;

  /// The date currently shown by the visit list.
  DateTime get selectedDate => _selectedDate;

  /// Fan choices exposed by the repository.
  List<OperatorFanOption> get fanOptions =>
      ref.read(operatorVisitRepositoryProvider).fanOptions();

  @override
  List<OperatorVisitRecord> build() {
    _selectedDate = DateTime.now();
    return ref.read(operatorVisitRepositoryProvider).listForDate(_selectedDate);
  }

  /// Adds a manual visit and refreshes the current-day list.
  void recordManualVisit({required String fanId, String note = ''}) {
    ref
        .read(operatorVisitRepositoryProvider)
        .recordManualVisit(fanId: fanId, visitedAt: DateTime.now(), note: note);
    _refresh();
  }

  /// Corrects a visit note in the mock adapter.
  void correctVisit({required String recordId, required String note}) {
    ref
        .read(operatorVisitRepositoryProvider)
        .correctVisit(recordId: recordId, note: note);
    _refresh();
  }

  /// Voids a visit with the provided reason.
  void voidVisit({required String recordId, required String reason}) {
    ref
        .read(operatorVisitRepositoryProvider)
        .voidVisit(recordId: recordId, reason: reason);
    _refresh();
  }

  void _refresh() {
    state = ref
        .read(operatorVisitRepositoryProvider)
        .listForDate(_selectedDate);
  }
}
