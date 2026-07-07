import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/feed/feed_repository.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the global feed's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value,
/// and can re-run the fetch via [refresh] (pull-to-refresh / retry) without the
/// screen owning any request state.
class FeedController extends AsyncNotifier<List<Post>> {
  @override
  Future<List<Post>> build() {
    return ref.watch(feedRepositoryProvider).fetchFeed();
  }

  /// Re-fetches the feed, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(feedRepositoryProvider).fetchFeed(),
    );
  }
}

/// Exposes the global feed [AsyncValue] and its [FeedController].
final feedControllerProvider =
    AsyncNotifierProvider<FeedController, List<Post>>(
      FeedController.new,
      retry: noRetry,
    );
