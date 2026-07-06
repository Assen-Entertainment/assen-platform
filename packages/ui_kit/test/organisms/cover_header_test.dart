// Widget tests for AssenCoverHeader: title/subtitle/badge/avatar slots render.
// Golden skip #31.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ui_kit/ui_kit.dart';

Widget _host(Widget child) => MaterialApp(
  theme: AssenTheme.light(),
  home: Scaffold(body: child),
);

void main() {
  group('AssenCoverHeader', () {
    testWidgets('renders the title and subtitle', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCoverHeader(title: '미오', subtitle: '@mio · 버추얼'),
        ),
      );
      expect(find.text('미오'), findsOneWidget);
      expect(find.text('@mio · 버추얼'), findsOneWidget);
    });

    testWidgets('renders the avatar and badge slots', (tester) async {
      await tester.pumpWidget(
        _host(
          const AssenCoverHeader(
            title: '미오',
            avatar: AssenAvatar(name: '미오'),
            badge: Icon(Icons.verified),
          ),
        ),
      );
      expect(find.byType(AssenAvatar), findsOneWidget);
      expect(find.byIcon(Icons.verified), findsOneWidget);
    });
  });
}
