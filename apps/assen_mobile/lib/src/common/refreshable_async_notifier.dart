/// A refresh mixin for the screen [AsyncNotifier]s.
///
/// Every screen controller duplicated the same `refresh()`:
/// `state = const AsyncValue.loading(); state = await AsyncValue.guard(...)`.
/// That hard reset to a bare loading state flashes the skeleton on every
/// pull-to-refresh, discarding the list already on screen (and its scroll
/// offset). [RefreshableAsyncNotifier] centralises the body and drops the
/// loading reset, so a refresh keeps the previous data visible while the
/// re-fetch is in flight and only surfaces the skeleton on the first load.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Adds a shared [refresh] to an [AsyncNotifier], preserving the current data
/// during the reload instead of flashing a loading skeleton.
///
/// Implementers provide [fetch] (the same call their `build` delegates to);
/// [refresh] re-runs it. Because the state is not reset to loading first, the
/// last good value stays on screen until the re-fetch resolves — the list keeps
/// its scroll offset and no skeleton flash occurs. The pull-to-refresh spinner
/// (`RefreshIndicator`, which awaits [refresh]) is the in-flight affordance.
///
/// Riverpod 3.x's `AsyncValue.copyWithPrevious` (loading-with-previous) is
/// `@internal`, so this public-API equivalent is used to the same end.
mixin RefreshableAsyncNotifier<T> on AsyncNotifier<T> {
  /// Performs the fetch that backs both `build` and [refresh].
  Future<T> fetch();

  /// Re-runs [fetch], keeping the previous value visible during the reload.
  Future<void> refresh() async {
    state = await AsyncValue.guard(fetch);
  }
}
