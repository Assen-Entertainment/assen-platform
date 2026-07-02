/// Typed HTTP client for the Assen Platform backend.
///
/// P0 skeleton: only the configuration value type exists. P6 generates the
/// endpoint methods and DTOs from the backend OpenAPI snapshot via
/// swagger_parser (CONSTRAINTS #15) into `src/generated/`; that directory is
/// owned by the generator and must not be edited by hand (CONSTRAINTS #32).
library;

export 'src/api_client_config.dart';
