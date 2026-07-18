import 'package:assen_mobile/src/api/api_providers.dart';
import 'package:assen_mobile/src/app/app.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// App entry point: mount the app under a Riverpod [ProviderScope].
void main() {
  // Fail fast on a release build with no API base URL (ASS-294), before any UI.
  assertApiBaseUrlConfigured();
  runApp(const ProviderScope(child: AssenApp()));
}
