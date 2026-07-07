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
/// crash or a stray "null". Use this only for *lenient* fields the server sends
/// with a default; a contract-required int should use [requireInt].
int asInt(Object? value) => switch (value) {
  final int v => v,
  final num v => v.toInt(),
  _ => 0,
};

/// Returns the required string stored at [key], or throws on absence/wrong type.
///
/// A contract-required `str` field: a *missing* key or a non-string value is a
/// backend field-name drift and throws [ArgumentError] so it surfaces as a load
/// error instead of a silent default. An empty string `""` is a valid value
/// (the caller may still degrade it — e.g. via [nonEmpty] — for display).
String requireString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String) {
    throw ArgumentError.value(
      json,
      'json',
      'required string field "$key" is missing or not a string',
    );
  }
  return value;
}

/// Returns the required int stored at [key], or throws on absence/wrong type.
///
/// A contract-required numeric field: any `num` is accepted (coerced with
/// [num.toInt]), but a *missing* key or a non-numeric value (including `bool`)
/// throws [ArgumentError] so a backend field-name drift surfaces as a load
/// error rather than a silent `0`.
int requireInt(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is int) return value;
  if (value is num) return value.toInt();
  throw ArgumentError.value(
    json,
    'json',
    'required int field "$key" is missing or not a number',
  );
}

/// Returns the required bool stored at [key], or throws on absence/wrong type.
///
/// A contract-required `bool` field: a *missing* key or a non-bool value throws
/// [ArgumentError] so a backend field-name drift surfaces as a load error
/// rather than a silent `false`.
bool requireBool(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! bool) {
    throw ArgumentError.value(
      json,
      'json',
      'required bool field "$key" is missing or not a bool',
    );
  }
  return value;
}

/// Coerces a JSON list value into a `List<String>`, or `const []` when absent.
///
/// The server sends `list[str]`, but a malformed *optional* row (a bare string
/// or null) must not split into characters or throw — it degrades to an empty
/// list. Shared coercion for [requireStringList]; use this directly only for a
/// lenient list field the server sends with a default.
List<String> stringList(Object? value) => value is List
    ? value.map((e) => e.toString()).toList(growable: false)
    : const <String>[];

/// Returns the required list at [key] as a `List<String>`, or throws.
///
/// A contract-required `list[str]` field: a *missing* key or a non-list value
/// throws [ArgumentError] so a backend field-name drift surfaces as a load
/// error. An empty list `[]` is a valid value (the empty state); each element
/// is coerced with `toString()` (see [stringList]).
List<String> requireStringList(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! List) {
    throw ArgumentError.value(
      json,
      'json',
      'required list field "$key" is missing or not a list',
    );
  }
  return stringList(value);
}

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
