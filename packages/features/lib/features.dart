/// Fan-facing feature modules for Assen Platform.
///
/// P3a adds the shared auth abstraction (`AuthRepository`/`AuthSession` and the
/// Riverpod 3.x providers) that the app routers guard against. The mock
/// implementation is in-memory; P3b swaps it for the real opaque-token client
/// through `authRepositoryProvider` with no caller changes (CONSTRAINTS #31).
/// All state uses Riverpod 3.x APIs; 2.x syntax is forbidden (CONSTRAINTS #40).
library;

export 'src/auth/auth_providers.dart';
export 'src/auth/auth_repository.dart';
export 'src/auth/auth_session.dart';
export 'src/auth/mock_auth_repository.dart';
export 'src/auth/session_store.dart';
export 'src/placeholder_feature.dart';
