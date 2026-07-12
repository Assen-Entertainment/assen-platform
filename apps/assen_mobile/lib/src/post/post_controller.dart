import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/common/refreshable_async_notifier.dart';
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
class PostController extends AsyncNotifier<Post>
    with RefreshableAsyncNotifier<Post> {
  /// Creates a controller for the post identified by [postId].
  PostController(this.postId);

  /// The post id whose detail this controller loads.
  final String postId;

  /// Guards against overlapping like toggles (a double-tap): a second toggle is
  /// ignored until the first resolves, so the optimistic count can't drift.
  bool _likeInFlight = false;

  @override
  Future<Post> build() {
    return ref.watch(postRepositoryProvider).fetchPost(postId);
  }

  @override
  Future<Post> fetch() => ref.read(postRepositoryProvider).fetchPost(postId);

  /// Toggles the caller's like on this post, optimistically.
  ///
  /// Flips [Post.liked] and nudges [Post.likeCount] immediately so the heart
  /// responds without waiting on the network, then reconciles with the server's
  /// authoritative `{liked, like_count}` — or rolls back to the pre-toggle post
  /// if the write fails. A no-op while the post is still loading or errored (no
  /// data to toggle) and while a previous toggle is still in flight.
  Future<void> toggleLike() async {
    final current = state.value;
    if (current == null || _likeInFlight) return;
    _likeInFlight = true;
    final target = !current.liked;
    final delta = target ? 1 : -1;
    final nextCount = current.likeCount + delta < 0
        ? 0
        : current.likeCount + delta;
    state = AsyncData(current.copyWith(liked: target, likeCount: nextCount));
    try {
      final result = await ref
          .read(postRepositoryProvider)
          .setLike(postId, liked: target);
      // Reconcile against the server's fresh count (covers an idempotent no-op
      // or a concurrent like from another device).
      state = AsyncData(
        current.copyWith(liked: result.liked, likeCount: result.likeCount),
      );
    } on Object {
      // The write failed: restore the pre-toggle post so the heart doesn't lie.
      state = AsyncData(current);
    } finally {
      _likeInFlight = false;
    }
  }

  /// Bumps the post's comment count after a new comment is posted.
  ///
  /// The comment thread ([PostCommentsController]) owns the list; this keeps
  /// the post header's "댓글 N" in step with an appended comment without a full
  /// re-fetch. A no-op while the post is still loading or errored.
  void noteCommentAdded() {
    final current = state.value;
    if (current == null) return;
    state = AsyncData(current.copyWith(commentCount: current.commentCount + 1));
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
class PostCommentsController extends AsyncNotifier<List<Comment>>
    with RefreshableAsyncNotifier<List<Comment>> {
  /// Creates a comments controller for the post identified by [postId].
  PostCommentsController(this.postId);

  /// The post id whose comments this controller loads.
  final String postId;

  @override
  Future<List<Comment>> build() {
    return ref.watch(postRepositoryProvider).fetchComments(postId);
  }

  @override
  Future<List<Comment>> fetch() =>
      ref.read(postRepositoryProvider).fetchComments(postId);

  /// Posts [body] as a comment and appends the server's saved comment.
  ///
  /// Not optimistic (unlike a like/follow): a comment carries server-assigned
  /// identity (id, author display name, timestamp), so the thread waits for the
  /// `CommentOut` and appends it — keeping the list oldest-first. On success it
  /// also nudges the post header's comment count
  /// ([PostController.noteCommentAdded]). Errors propagate so the composer can
  /// surface them and keep the fan's draft.
  Future<void> addComment(String body) async {
    final comment = await ref
        .read(postRepositoryProvider)
        .addComment(postId, body);
    final current = state.value ?? const <Comment>[];
    state = AsyncData([...current, comment]);
    ref.read(postControllerProvider(postId).notifier).noteCommentAdded();
  }
}

/// Exposes each post's comment thread [AsyncValue], keyed by post id.
final AsyncNotifierProviderFamily<PostCommentsController, List<Comment>, String>
postCommentsControllerProvider =
    AsyncNotifierProvider.family<PostCommentsController, List<Comment>, String>(
      PostCommentsController.new,
      retry: noRetry,
    );
