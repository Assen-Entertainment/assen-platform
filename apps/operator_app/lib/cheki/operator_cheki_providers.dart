import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:operator_app/cheki/operator_cheki_repository.dart';

/// Repository provider for operator cheki data.
final Provider<OperatorChekiRepository> operatorChekiRepositoryProvider =
    Provider<OperatorChekiRepository>(
      (ref) => InMemoryOperatorChekiRepository(),
    );

/// Controller provider for the O3 cheki record screen.
final operatorChekiControllerProvider =
    NotifierProvider<OperatorChekiController, List<OperatorChekiRecord>>(
      OperatorChekiController.new,
    );

/// Riverpod 3 controller that keeps today's cheki list fresh.
class OperatorChekiController extends Notifier<List<OperatorChekiRecord>> {
  /// Cast choices exposed by the repository.
  List<OperatorCastOption> get castOptions =>
      ref.read(operatorChekiRepositoryProvider).castOptions();

  /// Cheki kinds exposed by the repository.
  List<String> get chekiTypes =>
      ref.read(operatorChekiRepositoryProvider).chekiTypes();

  @override
  List<OperatorChekiRecord> build() =>
      ref.read(operatorChekiRepositoryProvider).listToday();

  /// Records a cheki and refreshes the list.
  void recordCheki({
    required String castId,
    required String chekiType,
    required int quantity,
  }) {
    ref
        .read(operatorChekiRepositoryProvider)
        .recordCheki(castId: castId, chekiType: chekiType, quantity: quantity);
    _refresh();
  }

  /// Corrects a cheki quantity in the mock adapter.
  void correctCheki({required String recordId, required int quantity}) {
    ref
        .read(operatorChekiRepositoryProvider)
        .correctCheki(recordId: recordId, quantity: quantity);
    _refresh();
  }

  /// Voids a cheki with the provided reason.
  void voidCheki({required String recordId, required String reason}) {
    ref
        .read(operatorChekiRepositoryProvider)
        .voidCheki(recordId: recordId, reason: reason);
    _refresh();
  }

  void _refresh() {
    state = ref.read(operatorChekiRepositoryProvider).listToday();
  }
}
