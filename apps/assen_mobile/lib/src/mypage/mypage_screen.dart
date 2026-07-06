import 'package:assen_mobile/src/common/placeholder_screen.dart';
import 'package:flutter/widgets.dart';

/// The 마이 (my page) tab (placeholder until the full account UI lands — M5).
///
/// Auth-gated: the router redirects signed-out viewers to the login wall before
/// this screen builds (see `router.dart`).
class MyPageScreen extends StatelessWidget {
  /// Creates the my-page tab.
  const MyPageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AssenPlaceholderScreen(
      title: '마이',
      message: '내 프로필과 계정 관리는 곧 제공됩니다.',
    );
  }
}
