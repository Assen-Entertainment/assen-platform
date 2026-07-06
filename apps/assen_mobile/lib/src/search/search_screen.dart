import 'package:assen_mobile/src/common/placeholder_screen.dart';
import 'package:flutter/widgets.dart';

/// The search tab (placeholder until the full search UI lands — M5).
class SearchScreen extends StatelessWidget {
  /// Creates the search tab.
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AssenPlaceholderScreen(
      title: '검색',
      message: '크리에이터와 콘텐츠 검색은 곧 제공됩니다.',
    );
  }
}
