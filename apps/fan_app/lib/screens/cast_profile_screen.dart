import 'package:fan_app/mock/fan_mock_data.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The cast profile detail (C3) — renders [AssenCastProfileTemplate] whole.
///
/// A pushed detail route (deep-linkable at `/cast/:id`): the template's own
/// Scaffold + AppBar + bottom CTA is exactly a detail page, so it is reused as
/// is, with [castId] resolved against the mock roster ([FanMockData]) and the
/// back/reserve callbacks wired to the router. Cold-starting `/cast/:id`
/// renders standalone; popping returns to whatever pushed it (or /home).
class CastProfileScreen extends StatelessWidget {
  /// Creates the cast profile for [castId].
  const CastProfileScreen({required this.castId, super.key});

  /// The cast id from the `/cast/:id` path.
  final String castId;

  @override
  Widget build(BuildContext context) {
    final cast = FanMockData.castById(castId);

    return AssenCastProfileTemplate(
      castName: cast.name,
      castHue: cast.hue,
      tagline: cast.tagline,
      isFavorite: cast.id == 'mio',
      onBack: () => _pop(context),
      onReserve: () => context.go(FanRoutes.reservation),
    );
  }

  void _pop(BuildContext context) {
    // Deep-link cold start has nothing to pop; fall back to the home tab so the
    // back affordance never dead-ends.
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(FanRoutes.home);
    }
  }
}
