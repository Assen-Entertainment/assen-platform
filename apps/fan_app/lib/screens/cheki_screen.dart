import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The cheki album tab (E1) — renders [AssenChekiAlbumTemplate] whole.
///
/// This template draws no bottom tab bar of its own (only an [AssenAppBar] over
/// the album grid), so it embeds cleanly under the router shell whose Scaffold
/// supplies the 5-tab bar — no double chrome. The empty-state CTA routes to the
/// schedule tab so a fan with no cheki can go find casts. Mock data is the
/// template's unified fictional set (screens.md mock rule).
class ChekiScreen extends StatelessWidget {
  /// Creates the cheki album tab.
  const ChekiScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AssenChekiAlbumTemplate(
      onExplore: () => context.go(FanRoutes.schedule),
    );
  }
}
