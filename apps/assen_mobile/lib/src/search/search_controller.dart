import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/search/search_repository.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the search tab's async lifecycle for the current query.
///
/// An [AsyncNotifier] whose value is the results for the latest [search] call:
/// the screen debounces keystrokes and calls [search], which resets to an empty
/// result for a blank term (the guidance state) or runs a fresh loading→data/
/// error cycle otherwise. Named [SearchResultsController] to avoid colliding
/// with Material's `SearchController`.
class SearchResultsController extends AsyncNotifier<SearchResult> {
  /// Monotonic id of the most recent [search] call.
  ///
  /// Each call claims the next value up front; a resolved request only commits
  /// its result (or loading transition) while it is still the latest claim.
  /// This defeats the out-of-order race where a slower request for a stale term
  /// (e.g. `mi`) resolves after a newer one (`mio`) and would otherwise
  /// overwrite the fresher results with older ones.
  int _requestId = 0;

  @override
  Future<SearchResult> build() async => const SearchResult.empty();

  /// Runs a search for [query], or clears to empty when it is blank.
  ///
  /// A blank/whitespace term short-circuits to an empty result (no request), so
  /// clearing the field returns to the guidance state instantly. Otherwise the
  /// state goes loading then resolves to data or an [AsyncError] via
  /// [AsyncValue.guard] — but only while this call is still the latest one, so
  /// a superseded in-flight request is dropped instead of clobbering newer
  /// state.
  Future<void> search(String query) async {
    final term = query.trim();
    final requestId = ++_requestId;
    if (term.isEmpty) {
      state = const AsyncData(SearchResult.empty());
      return;
    }
    state = const AsyncValue.loading();
    final result = await AsyncValue.guard(
      () => ref.read(searchRepositoryProvider).search(term),
    );
    // A newer search superseded this one while it was in flight; drop its
    // (now stale) result rather than overwrite the fresher state.
    if (requestId != _requestId) return;
    state = result;
  }
}

/// Exposes the search results [AsyncValue] and its [SearchResultsController].
final searchControllerProvider =
    AsyncNotifierProvider<SearchResultsController, SearchResult>(
      SearchResultsController.new,
      retry: noRetry,
    );
