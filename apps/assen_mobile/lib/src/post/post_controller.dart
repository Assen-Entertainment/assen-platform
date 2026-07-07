import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/post/comment.dart';
import 'package:assen_mobile/src/post/post.dart';
import 'package:assen_mobile/src/post/post_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// The family provider type returned by `AsyncNotifierProvider.family` lives in
// riverpod's `misc` library, not the default export; it is imported here so the
// providers can carry the explicit type the workspace ruleset requires.
import 'package:flutter_riverpod/misc.dart' show AsyncNotifierProviderFamily;

/// Drives one post detail's async lifecycle, keyed by post id.
///
/// A family [AsyncNotifier] (one instance per id) so each detail renders
/// loading/error/data from a single value and can re-run its fetch via
/// [refresh] (retry). The id argument is delivered to the notifier by the
/// family (Riverpod 3.x) and read back in [build].
class PostController extends AsyncNotifier<Post> {
  /// Creates a controller for the post identified by [postId].
  PostController(this.postId);

  /// The post id whose detail this controller loads.
  final String postId;

  @override
  Future<Post> build() {
    return ref.watch(postRepositoryProvider).fetchPost(postId);
  }

  /// Re-fetches the post, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(postRepositoryProvider).fetchPost(postId),
    );
  }
}

/// Exposes each post detail's [AsyncValue], keyed by post id.
final AsyncNotifierProviderFamily<PostController, Post, String>
postControllerProvider =
    AsyncNotifierProvider.family<PostController, Post, String>(
      PostController.new,
      retry: noRetry,
    );

/// Drives one post's comment thread, keyed by post id.
///
/// A separate family [AsyncNotifier] so the comments load and fail
/// independently of the post body — a comments fetch error renders an inline
/// retry without
/// hiding the post the caller came to read.
class PostCommentsController extends AsyncNotifier<List<Comment>> {
  /// Creates a comments controller for the post identified by [postId].
  PostCommentsController(this.postId);

  /// The post id whose comments this controller loads.
  final String postId;

  @override
  Future<List<Comment>> build() {
    return ref.watch(postRepositoryProvider).fetchComments(postId);
  }

  /// Re-fetches the comments, surfacing a fresh loading then data/error state.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(
      () => ref.read(postRepositoryProvider).fetchComments(postId),
    );
  }
}

/// Exposes each post's comment thread [AsyncValue], keyed by post id.
final AsyncNotifierProviderFamily<PostCommentsController, List<Comment>, String>
postCommentsControllerProvider =
    AsyncNotifierProvider.family<PostCommentsController, List<Comment>, String>(
      PostCommentsController.new,
      retry: noRetry,
    );
