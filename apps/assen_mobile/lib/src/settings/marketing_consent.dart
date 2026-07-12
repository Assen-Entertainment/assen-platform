import 'package:flutter/foundation.dart';

/// The fan's per-channel marketing opt-in state (`GET/PUT /api/fan/marketing`).
///
/// The app-side view model for the backend `MarketingConsentOut`/`In` shape
/// (D8, optional consent). `email` is reported for forward compatibility but is
/// not collected yet, so the settings UI renders its toggle disabled and never
/// sends on it. Consent is optional — any combination (including all-off) is
/// valid and never blocks service use.
@immutable
class MarketingConsent {
  /// Creates a per-channel consent snapshot.
  const MarketingConsent({
    required this.push,
    required this.sms,
    required this.email,
  });

  /// Builds a [MarketingConsent] from a `MarketingConsentOut` JSON object.
  ///
  /// Each channel falls back to its fail-closed default (`false`, opted out)
  /// when absent, so a partial payload never reports a fan as opted in.
  factory MarketingConsent.fromJson(Map<String, dynamic> json) =>
      MarketingConsent(
        push: json['push'] as bool? ?? false,
        sms: json['sms'] as bool? ?? false,
        email: json['email'] as bool? ?? false,
      );

  /// Whether push (앱 알림) marketing is opted in.
  final bool push;

  /// Whether SMS (문자) marketing is opted in.
  final bool sms;

  /// Whether email marketing is opted in (not collected yet — UI-disabled).
  final bool email;

  /// The `MarketingConsentIn` body — the server writes all three at once.
  Map<String, dynamic> toJson() => {'push': push, 'sms': sms, 'email': email};

  /// Returns a copy with the given channels overridden.
  MarketingConsent copyWith({bool? push, bool? sms, bool? email}) =>
      MarketingConsent(
        push: push ?? this.push,
        sms: sms ?? this.sms,
        email: email ?? this.email,
      );
}
