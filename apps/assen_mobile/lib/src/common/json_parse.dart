/// Shared JSON-parsing and number-formatting helpers for the hand-written view
/// models (`Creator`, `Product`, `FanMe`, …).
///
/// These are the small primitives the model factories previously duplicated as
/// private statics; extracting them here keeps one definition of "empty string
/// means absent", "coerce a numeric to a non-negative int" and "group a count
/// with thousands separators" so the models stay consistent. When the generated
/// `api_client` DTOs (P6) land they replace the parsing that uses these.
library;

/// Returns [value] when it is a non-empty string, otherwise null.
///
/// The server sends `""` (not omission) for an unset descriptor; an empty
/// avatar URL, category or bio should read as absent — an initials fallback and
/// no subtitle — rather than a broken image or a dangling separator.
String? nonEmpty(String? value) =>
    (value != null && value.isNotEmpty) ? value : null;

/// Coerces a numeric field to an int, defaulting to 0 for a missing/wrong type.
///
/// Accepts the server's `int` (and any other `num`) and degrades a
/// missing/`null`/wrong-typed value to 0 so a count or price never renders as a
/// crash or a stray "null".
int asInt(Object? value) => switch (value) {
  final int v => v,
  final num v => v.toInt(),
  _ => 0,
};

/// Returns the list stored at [key], or throws when the contract is violated.
///
/// The envelope contract guarantees the array key is present — an *empty* array
/// is the empty state, whereas a *missing* key (or a non-list value) is a
/// backend field-name drift. This throws [ArgumentError] so that drift surfaces
/// as a load error instead of a silently-empty result that hides the mismatch.
/// Used by the newer strict envelopes (search/notifications); the discovery
/// repository keeps a deliberately lenient default for its own `items`.
List<dynamic> requireList(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! List) {
    throw ArgumentError.value(
      json,
      'json',
      'envelope is missing the required "$key" array',
    );
  }
  return value;
}

/// Formats [value] with thousands separators (e.g. `1,284`, `-2,000`).
///
/// A local formatter (the app has no `intl` dependency) so a count or price
/// always renders grouped rather than as a bare run of digits. Negative values
/// keep a leading `-`.
String formatThousands(int value) {
  final digits = value.abs().toString();
  final buffer = StringBuffer(value < 0 ? '-' : '');
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buffer.write(',');
    buffer.write(digits[i]);
  }
  return buffer.toString();
}
