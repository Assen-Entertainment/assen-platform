import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/studio/studio_posts_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Drives the 게시물 관리 (studio posts) screen's async lifecycle.
///
/// An [AsyncNotifier] so the screen renders loading/error/data from one value
/// and can re-run the fetch via [refresh] (retry). A signed-out caller surfaces
/// as a StudioAuthRequiredException, a signed-in non-owner as a
/// StudioOwnerRequiredException, which the screen maps to its two states.
class StudioPostsController extends AsyncNotifier<List<Post>>
    with RefreshableAsyncNotifier<List<Post>> {
  @override
  Future<List<Post>> build() =>
      ref.watch(studioPostsRepositoryProvider).fetchPosts();

  @override
  Future<List<Post>> fetch() =>
      ref.read(studioPostsRepositoryProvider).fetchPosts();
}

/// Exposes the owner's posts [AsyncValue] and its controller.
final studioPostsControllerProvider =
    AsyncNotifierProvider<StudioPostsController, List<Post>>(
      StudioPostsController.new,
      retry: noRetry,
    );
