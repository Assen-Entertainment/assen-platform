import 'package:flutter/material.dart';
import 'package:ui_kit/ui_kit.dart';

/// Standalone entrypoint for the ASS-88 design-system catalogue (review).
///
/// Run with `flutter run -t lib/catalog_main.dart` or build the web bundle with
/// `flutter build web -t lib/catalog_main.dart`. It boots the [AtomCatalog],
/// [MoleculeCatalog] and [OrganismCatalog] under the Assen light theme so every
/// atom, molecule and organism is rendered for human/design review — separate
/// from the real app `main.dart`.
void main() {
  runApp(const _CatalogApp());
}

class _CatalogApp extends StatelessWidget {
  const _CatalogApp();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Assen Design System',
      debugShowCheckedModeBanner: false,
      theme: AssenTheme.light(),
      home: const DefaultTabController(
        length: 3,
        child: Scaffold(
          body: TabBarView(
            children: [AtomCatalog(), MoleculeCatalog(), OrganismCatalog()],
          ),
          bottomNavigationBar: SafeArea(
            child: TabBar(
              tabs: [
                Tab(text: 'Atoms'),
                Tab(text: 'Molecules'),
                Tab(text: 'Organisms'),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
