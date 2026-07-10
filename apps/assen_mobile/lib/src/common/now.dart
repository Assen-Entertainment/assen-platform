/// The wall-clock "now" used to derive relative timestamps, injected rather
/// than read inside `build`.
///
/// Screens that render relative times (feed, notifications, orders, post) used
/// to call `DateTime.now()` directly inside a widget's `build`. That recomputes
/// on every rebuild and makes widget tests time-dependent (a fixed fixture
/// drifts as the wall clock moves). Reading [nowProvider] instead pins one
/// instant per screen build and lets a test override it with a fixed value for
/// deterministic relative-time assertions.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The reference instant for relative-time formatting.
///
/// Resolves to `DateTime.now()` at first read and stays fixed until the
/// provider is invalidated, so relative labels are not recomputed on every
/// rebuild. Override this in tests (`nowProvider.overrideWithValue(...)`) to
/// make "N분 전" style output deterministic.
final nowProvider = Provider<DateTime>((ref) => DateTime.now());
