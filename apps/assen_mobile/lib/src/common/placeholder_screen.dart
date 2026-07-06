import 'package:flutter/material.dart';
import 'package:ui_kit/ui_kit.dart';

/// A "준비 중" (coming soon) screen used by the tabs and routes whose full UI is
/// out of scope for this milestone (the 13-screen surface is M5).
///
/// It reuses the ui_kit shell chrome (app bar + empty state) so each stub
/// reads as a finished frame with content pending, not a blank page.
class AssenPlaceholderScreen extends StatelessWidget {
  /// Creates a placeholder titled [title] with body copy [message].
  ///
  /// Pass [onBack] for pushed routes (creator profile); omit it on tab roots,
  /// which have no back affordance.
  const AssenPlaceholderScreen({
    required this.title,
    required this.message,
    this.onBack,
    super.key,
  });

  /// The app-bar title.
  final String title;

  /// The empty-state body copy explaining what will live here.
  final String message;

  /// Optional back handler; when set the app bar shows a back button.
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AssenAppBar(title: title, onBack: onBack),
      body: AssenEmptyState(title: '준비 중이에요', message: message),
    );
  }
}
