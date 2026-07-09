import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// Which parts of the lockup to render.
enum AssenLogoVariant {
  /// Mark + wordmark (the default brand lockup).
  full,

  /// The A-peak mark only (compact — app-bar leading, chips, favicons).
  mark,

  /// The "Assen" wordmark only.
  wordmark,
}

/// Lockup size — drives the mark tile and the wordmark scale.
enum AssenLogoSize {
  /// Compact (app-bar / inline).
  sm,

  /// Default.
  md,

  /// Brand front-door (login / onboarding hero).
  lg,
}

/// The Assen brand lockup — the rising "A-peak" mark + "Assen" wordmark.
///
/// The Flutter counterpart of the web `logo.tsx` (the single source of brand
/// truth): a mark shaped as an ascending "A" peak — a creator rising to the
/// stage — sharing its geometry with the web favicon. The mark sits on the
/// sanctioned brand-gradient tile ([AssenGradients.brand], the tokens.md
/// 2026-07-09 exception) with a white stroke, so it reads the same in light or
/// on a dark hero. [mono] drops the tile and strokes the mark in the ambient
/// text colour (footers, chips, single-colour contexts).
///
/// This is the ONE place mobile draws the brand identity: before it, a grep of
/// the app + ui_kit for a logo/wordmark returned nothing, so web and mobile
/// told two brand stories. Placing it in the discovery app bar and login closes
/// that expression gap.
class AssenLogo extends StatelessWidget {
  /// Creates the Assen lockup.
  const AssenLogo({
    this.variant = AssenLogoVariant.full,
    this.size = AssenLogoSize.md,
    this.mono = false,
    this.color,
    this.label = 'Assen',
    super.key,
  });

  /// full = mark + wordmark, mark = tile only, wordmark = text only.
  final AssenLogoVariant variant;

  /// Lockup scale — see [AssenLogoSize].
  final AssenLogoSize size;

  /// Single-colour lockup: drops the gradient tile and strokes the mark in
  /// [color] (or the ambient text colour). For mono/coloured backgrounds.
  final bool mono;

  /// The wordmark + mono-mark colour. Defaults to the ambient
  /// [DefaultTextStyle] colour, falling back to ink.900.
  final Color? color;

  /// Accessibility label announced for the whole lockup.
  final String label;

  double get _markPx => switch (size) {
    AssenLogoSize.sm => 22,
    AssenLogoSize.md => 26,
    AssenLogoSize.lg => 34,
  };

  double get _wordSize => switch (size) {
    AssenLogoSize.sm => TypographyTokens.titleMSize,
    AssenLogoSize.md => TypographyTokens.titleLSize,
    AssenLogoSize.lg => TypographyTokens.displayMSize,
  };

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final inkColor =
        color ?? DefaultTextStyle.of(context).style.color ?? colors.ink900;

    final wordmark = Text(
      'Assen',
      style: TextStyle(
        fontFamily: TypographyTokens.displayFontFamily,
        fontFamilyFallback: TypographyTokens.displayFontFamilyFallback,
        fontSize: _wordSize,
        fontWeight: FontWeight.w700,
        letterSpacing: _wordSize * -0.02,
        height: 1,
        color: inkColor,
      ),
    );

    final content = switch (variant) {
      AssenLogoVariant.wordmark => wordmark,
      AssenLogoVariant.mark => _Mark(px: _markPx, mono: mono, color: inkColor),
      AssenLogoVariant.full => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _Mark(px: _markPx, mono: mono, color: inkColor),
          SizedBox(width: _markPx * 0.3),
          wordmark,
        ],
      ),
    };

    return Semantics(
      label: label,
      image: true,
      excludeSemantics: true,
      child: content,
    );
  }
}

/// The A-peak mark — a gradient tile (or, when [mono], a bare stroke).
class _Mark extends StatelessWidget {
  const _Mark({required this.px, required this.mono, required this.color});

  final double px;
  final bool mono;
  final Color color;

  @override
  Widget build(BuildContext context) {
    if (mono) {
      return SizedBox(
        width: px,
        height: px,
        child: CustomPaint(painter: _AssenMarkPainter(color)),
      );
    }
    final inner = px * 0.62;
    return Container(
      width: px,
      height: px,
      decoration: BoxDecoration(
        gradient: AssenGradients.brand,
        borderRadius: BorderRadius.all(Radius.circular(px * 0.28)),
        boxShadow: const [
          BoxShadow(
            color: ElevationTokens.level1Color,
            offset: Offset(
              ElevationTokens.level1OffsetX,
              ElevationTokens.level1OffsetY,
            ),
            blurRadius: ElevationTokens.level1Blur,
          ),
        ],
      ),
      alignment: Alignment.center,
      child: SizedBox(
        width: inner,
        height: inner,
        child: const CustomPaint(
          painter: _AssenMarkPainter(AssenGradients.onBrand),
        ),
      ),
    );
  }
}

/// Strokes the ascending "A" — identical geometry to the web favicon/logo path
/// `M10 23 L16 8.5 L22 23 M12.6 17.6 H19.4` in a 32×32 space.
class _AssenMarkPainter extends CustomPainter {
  const _AssenMarkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / 32.0;
    canvas.scale(scale);
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final path = Path()
      ..moveTo(10, 23)
      ..lineTo(16, 8.5)
      ..lineTo(22, 23)
      ..moveTo(12.6, 17.6)
      ..lineTo(19.4, 17.6);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_AssenMarkPainter oldDelegate) =>
      oldDelegate.color != color;
}
