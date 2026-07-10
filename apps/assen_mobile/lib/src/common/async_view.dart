/// A thin renderer for the loading/error/empty/data lifecycle of an
/// [AsyncValue], shared by every read screen.
///
/// Every screen used to inline the same four-branch `value.when(...)`: a
/// bespoke skeleton, a verbatim [AssenErrorState] ("불러오지 못했어요" /
/// "네트워크 상태를 확인..."), an optional empty state, and the loaded body.
/// [AssenAsyncView] keeps the per-screen bits as slots (`loading`, `empty`,
/// `data`) and centralises the error branch: [errorMessageFor] picks the copy,
/// and an `errorBuilder` lets a screen special-case a domain error (e.g. an
/// auth-required or not-found exception) before falling back to the default.
library;

import 'package:assen_mobile/src/common/error_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ui_kit/ui_kit.dart';

/// Renders [value]'s loading/error/empty/data states with shared error copy.
///
/// A refresh keeps the previous data on screen (no skeleton flash) because the
/// `RefreshableAsyncNotifier` controllers do not reset to a loading state on
/// refresh; the loading slot is only shown for the first load.
class AssenAsyncView<T> extends StatelessWidget {
  /// Creates an async view over [value].
  ///
  /// [loading] is shown for the first load; [data] renders the loaded value.
  /// Provide [onRetry] to wire the default error state's retry CTA. Pass
  /// [isEmpty] with [empty] to render an empty state for a "loaded but blank"
  /// value. Override [errorTitle]/[errorMessage] for per-screen copy, or
  /// [errorBuilder] to fully replace the error branch for specific errors.
  const AssenAsyncView({
    required this.value,
    required this.loading,
    required this.data,
    this.onRetry,
    this.errorTitle = '불러오지 못했어요',
    this.errorMessage,
    this.errorBuilder,
    this.isEmpty,
    this.empty,
    super.key,
  });

  /// The async state to render.
  final AsyncValue<T> value;

  /// The first-load placeholder (typically a skeleton).
  final Widget loading;

  /// Builds the loaded body from the resolved value.
  final Widget Function(T value) data;

  /// The default error state's retry handler; null hides the retry CTA.
  final VoidCallback? onRetry;

  /// The default error state's headline. Defaults to "불러오지 못했어요".
  final String errorTitle;

  /// Overrides the default error message; falls back to [errorMessageFor].
  final String Function(Object error)? errorMessage;

  /// Special-cases the error branch: return a widget to replace the default
  /// error state (e.g. an auth-required empty state), or null to fall through
  /// to the default [AssenErrorState].
  final Widget? Function(Object error, StackTrace stackTrace)? errorBuilder;

  /// Whether a loaded [value] should render [empty] instead of [data].
  final bool Function(T value)? isEmpty;

  /// The empty-state slot, used when [isEmpty] returns true.
  final Widget Function()? empty;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => loading,
      error: (error, stackTrace) {
        final override = errorBuilder?.call(error, stackTrace);
        if (override != null) return override;
        return AssenErrorState(
          title: errorTitle,
          message: (errorMessage ?? errorMessageFor)(error),
          onRetry: onRetry,
        );
      },
      data: (resolved) {
        if (isEmpty != null && isEmpty!(resolved)) {
          return empty?.call() ?? const SizedBox.shrink();
        }
        return data(resolved);
      },
    );
  }
}
