import 'package:assen_mobile/src/common/placeholder_screen.dart';
import 'package:flutter/widgets.dart';

/// The notifications tab (placeholder until the full activity feed lands — M5).
class NotificationsScreen extends StatelessWidget {
  /// Creates the notifications tab.
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AssenPlaceholderScreen(
      title: '알림',
      message: '활동과 소식 알림은 곧 제공됩니다.',
    );
  }
}
