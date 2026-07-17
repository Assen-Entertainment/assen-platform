import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The server error code refusing a gated interaction from an unverified fan.
///
/// Raised as a 403 by the backend's `require_kyc_verified` (see
/// `config/errors.py`) on follow/like/comment/subscribe/order/studio-profile
/// writes. Reading stays open, and the verify endpoints themselves are never
/// gated, so a fan can always reach the verified state.
const String kycGateErrorCode = 'IdentityVerificationRequired';

/// Whether the server has refused a gated interaction pending 본인인증.
///
/// The single, global 본인인증 gate (mirroring the web's one `VerifyGate`): the
/// shared Dio `KycGateInterceptor` raises this the moment ANY call comes back
/// 403 [kycGateErrorCode], and the router redirects to the verify screen in
/// response — so no call site re-implements the gate. The verify screen
/// [KycGateController.clear]s it when the fan finishes (or backs out),
/// releasing the redirect.
///
/// Holds no PII: it is a bare flag, never the refused request or its body.
class KycGateController extends Notifier<bool> {
  @override
  bool build() => false;

  /// Signals that 본인인증 is required (idempotent — a burst of gated calls
  /// raises the same flag once).
  void raise() => state = true;

  /// Releases the gate (verification completed, or the fan backed out).
  void clear() => state = false;
}

/// Exposes the 본인인증 gate flag and its [KycGateController].
final kycGateProvider = NotifierProvider<KycGateController, bool>(
  KycGateController.new,
);
