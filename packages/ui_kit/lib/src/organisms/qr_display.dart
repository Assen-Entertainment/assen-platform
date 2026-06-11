import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/button.dart';
import 'package:ui_kit/src/atoms/progress.dart';
import 'package:ui_kit/src/molecules/notice_bar.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3).
const double _qrTitleSize = 16; // tokens.md §3 title.m — sheet title
const double _qrTimerSize = 13; // tokens.md §3 label — countdown caption
const double _qrExpiredSize = 14; // tokens.md §3 body.m — expired notice

/// Lifecycle of an [AssenQrDisplay] (active vs. expired).
enum AssenQrStatus {
  /// The QR is current — within its rotation window.
  active,

  /// The QR has expired — the code is hidden behind a refresh prompt.
  expired,
}

/// The rotating QR check-in panel (`회전 QR + 갱신 타이머 링 + 만료`).
///
/// Covers the Domain/QRDisplay row of `components.md` and the check-in screen
/// (screens.md B1). It presents a short-lived QR for staff to scan: the actual
/// matrix is a placeholder here (the real payload renders downstream), shown
/// inside a ring whose remaining sweep is the rotation [progress]. An auto-
/// brightness notice (휘도 상향) explains the screen will brighten for scanning
/// (references §3 채택 #7). When [status] is expired the code is masked behind a
/// refresh prompt wired to [onRefresh], so a stale code is never presented.
class AssenQrDisplay extends StatelessWidget {
  /// Creates a QR display in the [status] state.
  ///
  /// [memberNumber] is shown under the code for manual fallback.
  /// [remainingLabel] is the formatted countdown (e.g. "29초"); [progress] is
  /// the 0–1 fraction of the rotation window left, driving the ring.
  /// [onRefresh] re-issues an expired code. [size] is the QR edge length.
  const AssenQrDisplay({
    required this.memberNumber,
    this.status = AssenQrStatus.active,
    this.remainingLabel,
    this.progress = 1,
    this.onRefresh,
    this.size = 220,
    super.key,
  });

  /// The membership number shown beneath the code (manual fallback).
  final String memberNumber;

  /// Whether the code is active or expired — see [AssenQrStatus].
  final AssenQrStatus status;

  /// The formatted time-left caption (e.g. "29초"). Active state only.
  final String? remainingLabel;

  /// Fraction of the rotation window remaining (0–1), driving the timer ring.
  final double progress;

  /// Re-issues an expired code; required for the expired state's prompt.
  final VoidCallback? onRefresh;

  /// The QR edge length in logical pixels.
  final double size;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isExpired = status == AssenQrStatus.expired;

    // 컨테이너 시맨틱스 — 스크린리더가 회원증 QR임을 한 번에 읽도록.
    return Semantics(
      container: true,
      label: '$memberNumber 회원증 QR',
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Auto-brightness affordance — the standard membership-QR behaviour
          // (references §3 채택 #7). Copy only; the real brighten is host-side.
          const AssenNoticeBar(
            message: '스캔을 위해 화면 밝기를 자동으로 높입니다.',
            icon: Icons.brightness_high_outlined,
          ),
          const SizedBox(height: SpacingTokens.s5),
          SizedBox(
            width: size,
            height: size,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // Rotation timer ring — remaining sweep of the active window.
                if (!isExpired)
                  Positioned.fill(
                    child: AssenProgressDonut(
                      value: progress,
                      size: size,
                      strokeWidth: SpacingTokens.s1,
                    ),
                  ),
                // QR placeholder — token stand-in for the real matrix.
                Container(
                  width: size - SpacingTokens.s8,
                  height: size - SpacingTokens.s8,
                  decoration: BoxDecoration(
                    color: colors.white,
                    borderRadius: const BorderRadius.all(
                      Radius.circular(RadiusTokens.md),
                    ),
                    border: Border.all(color: colors.ink100),
                  ),
                  alignment: Alignment.center,
                  child: Icon(
                    Icons.qr_code_2,
                    size: size - SpacingTokens.s16,
                    color: isExpired ? colors.ink200 : colors.ink900,
                  ),
                ),
                if (isExpired)
                  _ExpiredOverlay(colors: colors, onRefresh: onRefresh),
              ],
            ),
          ),
          const SizedBox(height: SpacingTokens.s4),
          Text(
            memberNumber,
            style: TextStyle(
              fontSize: _qrTitleSize,
              fontWeight: FontWeight.w600,
              letterSpacing: 1,
              color: colors.ink700,
            ),
          ),
          const SizedBox(height: SpacingTokens.s2),
          // liveRegion — 만료/갱신 전이가 스크린리더에 자동 안내되도록.
          if (isExpired)
            Semantics(
              liveRegion: true,
              child: Text(
                '코드가 만료되었습니다.',
                style: TextStyle(
                  fontSize: _qrExpiredSize,
                  fontWeight: FontWeight.w600,
                  color: colors.redInk,
                ),
              ),
            )
          else if (remainingLabel != null)
            Semantics(
              liveRegion: true,
              child: Text(
                '$remainingLabel 후 코드가 갱신됩니다',
                style: TextStyle(
                  fontSize: _qrTimerSize,
                  fontWeight: FontWeight.w600,
                  color: colors.ink500,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// The frosted overlay shown over an expired QR with a refresh prompt.
class _ExpiredOverlay extends StatelessWidget {
  const _ExpiredOverlay({required this.colors, required this.onRefresh});

  final AssenColors colors;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.cream50.withValues(alpha: 0.82),
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
      ),
      child: Center(
        child: AssenButton(
          label: '코드 새로 고침',
          icon: Icons.refresh,
          style: AssenButtonStyle.secondary,
          onPressed: onRefresh,
        ),
      ),
    );
  }
}
