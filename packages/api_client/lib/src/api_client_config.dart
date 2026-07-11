/// Connection settings the generated client (P6) will be constructed with.
///
/// Kept tiny and hand-written so the generated layer can depend on a stable
/// configuration type without owning environment concerns.
class ApiClientConfig {
  /// Creates a configuration pointing at [baseUrl].
  ///
  /// [baseUrl] must be an absolute http/https URL; a relative or non-http URL
  /// throws [ArgumentError] so misconfiguration fails fast at startup. The
  /// scheme is matched exactly (not `startsWith('http')`, which also admitted
  /// `httpx://` and other `http`-prefixed schemes — ASS-296).
  ApiClientConfig({required this.baseUrl}) {
    final uri = Uri.tryParse(baseUrl);
    if (uri == null ||
        !uri.isAbsolute ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      throw ArgumentError.value(
        baseUrl,
        'baseUrl',
        'must be an absolute http(s) URL',
      );
    }
  }

  /// Absolute base URL of the backend API, e.g. `https://api.assen.example`.
  final String baseUrl;
}
