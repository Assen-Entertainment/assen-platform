import 'package:features/src/auth/session_store.dart';

/// Creates the default non-web session store.
///
/// Native targets keep P3a mock auth in memory; durable secure storage belongs
/// to the real auth track (ASS-90/91), not this local preview bridge.
SessionStore createPlatformSessionStore() => InMemorySessionStore();
