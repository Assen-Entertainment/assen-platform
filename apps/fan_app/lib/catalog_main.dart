import 'package:flutter/material.dart';
import 'package:ui_kit/ui_kit.dart';

/// Standalone entrypoint for the ASS-88 atom catalogue (visual review).
///
/// Run with `flutter run -t lib/catalog_main.dart` or build the web bundle with
/// `flutter build web -t lib/catalog_main.dart`. It boots the [AtomCatalog]
/// under the Assen light theme so every atom is rendered on one screen for
/// human/design review — separate from the real app `main.dart`.
void main() {
  runApp(const _CatalogApp());
}

class _CatalogApp extends StatelessWidget {
  const _CatalogApp();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assen Atoms',
      debugShowCheckedModeBanner: false,
      theme: AssenTheme.light(),
      home: const AtomCatalog(),
    );
  }
}
