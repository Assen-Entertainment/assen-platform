/// Operator-only feature modules for Assen Platform.
///
/// Consumed exclusively by operator_app; fan_app must never import this package
/// (staff-only surfaces). P0 placeholder proves the wiring; real operator
/// console features land from P5. Riverpod 3.x only (CONSTRAINTS #40).
library;

export 'src/placeholder_dashboard.dart';
