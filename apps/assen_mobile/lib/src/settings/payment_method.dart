import 'package:flutter/foundation.dart';

/// A fan's saved payment method — display metadata only, never a PAN (R3/PCI).
///
/// The app-side view model for the backend `PaymentMethodOut` shape
/// (`GET /api/fan/payment-methods`). Only the card [brand] + [last4] + the
/// [isPrimary] flag are ever exposed; the full card number never leaves the
/// server (the mock tokenizer discards it). Registering a method is a
/// 대표·법무·PG gate and is deliberately not offered from the app yet.
@immutable
class PaymentMethod {
  /// Creates a saved-payment-method summary.
  const PaymentMethod({
    required this.id,
    required this.brand,
    required this.last4,
    required this.isPrimary,
  });

  /// Builds a [PaymentMethod] from a `PaymentMethodOut` JSON object.
  ///
  /// The contract requires an [id]; [brand]/[last4] fall back to empty and
  /// [isPrimary] to false so a partial payload renders a safe (non-primary) row
  /// rather than throwing on display-only fields.
  factory PaymentMethod.fromJson(Map<String, dynamic> json) {
    final dynamic id = json['id'];
    if (id == null) {
      throw ArgumentError('payment-method payload is missing a required "id"');
    }
    return PaymentMethod(
      id: id.toString(),
      brand: json['brand'] as String? ?? '',
      last4: json['last4'] as String? ?? '',
      isPrimary: json['is_primary'] as bool? ?? false,
    );
  }

  /// The saved method's stable id (server `id`).
  final String id;

  /// The card network/brand for display (e.g. "VISA"); may be empty.
  final String brand;

  /// The last 4 digits for display — never the full PAN.
  final String last4;

  /// Whether this is the fan's primary method (at most one per fan).
  final bool isPrimary;

  /// A masked label for display, e.g. `VISA ····1234`.
  String get maskedLabel {
    final network = brand.isEmpty ? '카드' : brand;
    return '$network ····$last4';
  }
}
