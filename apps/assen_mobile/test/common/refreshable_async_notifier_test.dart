import 'dart:async';

import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

/// A minimal notifier exercising the mixin. [fetch] returns [gate]'s future
/// when a test sets it (to hold a refresh in flight), else the next value.
class _Counter extends AsyncNotifier<int> with RefreshableAsyncNotifier<int> {
  int next = 1;
  Completer<int>? gate;

  @override
  Future<int> build() => fetch();

  @override
  Future<int> fetch() {
    final g = gate;
    return g != null ? g.future : Future<int>.value(next);
  }
}

final _counterProvider = AsyncNotifierProvider<_Counter, int>(_Counter.new);

void main() {
  test('refresh keeps the previous data visible during the reload', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    // Initial build resolves to AsyncData(1).
    expect(await container.read(_counterProvider.future), 1);
    expect(container.read(_counterProvider), const AsyncData<int>(1));

    // Gate the next fetch so the refresh stays in flight while observing.
    final notifier = container.read(_counterProvider.notifier);
    final gate = Completer<int>();
    notifier.gate = gate;
    final refreshing = notifier.refresh();

    // The headline contract: state is NOT reset to loading — the previous data
    // (and, on a real screen, its scroll offset) stays put during the re-fetch.
    expect(container.read(_counterProvider), const AsyncData<int>(1));
    expect(container.read(_counterProvider).isLoading, isFalse);

    gate.complete(2);
    await refreshing;
    expect(container.read(_counterProvider), const AsyncData<int>(2));
  });

  test('a failed refresh surfaces the error (no silent stale data)', () async {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    expect(await container.read(_counterProvider.future), 1);

    final notifier = container.read(_counterProvider.notifier);
    final gate = Completer<int>();
    notifier.gate = gate;
    final refreshing = notifier.refresh();
    gate.completeError(StateError('reload failed'));
    await refreshing;

    expect(container.read(_counterProvider).hasError, isTrue);
  });
}
