import 'package:flutter_test/flutter_test.dart';
import 'package:operator_app/router/operator_router.dart';
import 'package:operator_app/router/routes.dart';
import 'package:operator_app/shell/operator_shell.dart';

void main() {
  group('shellIndexForLocation', () {
    test('maps each console route to its destination index', () {
      expect(shellIndexForLocation(OperatorRoutes.dashboard), 0);
      expect(shellIndexForLocation(OperatorRoutes.checkin), 1);
      expect(shellIndexForLocation(OperatorRoutes.cheki), 2);
      expect(shellIndexForLocation(OperatorRoutes.schedule), 3);
      expect(shellIndexForLocation(OperatorRoutes.reports), 4);
      expect(shellIndexForLocation(OperatorRoutes.pos), 5);
    });

    test('resolves the similar /checkin and /cheki routes distinctly', () {
      // They share a leading substring but neither is a prefix of the other;
      // exact-or-slash-boundary matching keeps them on separate indices.
      expect(shellIndexForLocation('/checkin'), 1);
      expect(shellIndexForLocation('/cheki'), 2);
    });

    test('resolves a sub-path to its parent destination', () {
      expect(shellIndexForLocation('/cheki/detail'), 2);
    });

    test('falls back to the dashboard for non-shell locations', () {
      expect(shellIndexForLocation(OperatorRoutes.login), 0);
      expect(shellIndexForLocation(OperatorRoutes.admin), 0);
      expect(shellIndexForLocation('/unknown'), 0);
    });

    test('round-trips every destination index through its location', () {
      for (var i = 0; i < shellLocations.length; i++) {
        expect(shellIndexForLocation(shellLocations[i]), i);
      }
    });
  });

  test('shellLocations aligns 1:1 with OperatorShell.destinations', () {
    // The router branch order and the shell nav order are parallel lists; if
    // one is reordered or extended without the other, navigation desyncs.
    expect(shellLocations.length, OperatorShell.destinations.length);
  });
}
