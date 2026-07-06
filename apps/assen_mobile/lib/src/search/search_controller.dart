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
  @override
  Future<SearchResult> build() async => const SearchResult.empty();

  /// Runs a search for [query], or clears to empty when it is blank.
  ///
  /// A blank/whitespace term short-circuits to an empty result (no request), so
  /// clearing the field returns to the guidance state instantly. Otherwise the
  /// state goes loading then resolves to data or an [AsyncError] via
  /// [AsyncValue.guard].
  Future<void> search(String query) async {
    final term = query.trim();
    if (term.isEmpty) {
      state = const AsyncData(SearchResult.empty());
      return;
    }
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(searchRepositoryProvider).search(term),
    );
  }
}

/// Exposes the search results [AsyncValue] and its [SearchResultsController].
final searchControllerProvider =
    AsyncNotifierProvider<SearchResultsController, SearchResult>(
      SearchResultsController.new,
      retry: noRetry,
    );
