import 'package:assen_mobile/src/app/app.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// App entry point: mount the app under a Riverpod [ProviderScope].
void main() {
  runApp(const ProviderScope(child: AssenApp()));
}
