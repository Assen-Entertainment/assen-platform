import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';

/// The three avatar sizes from `components.md` (Content/Avatar — size S/M/L).
enum AssenAvatarSize {
  /// 32dp — dense lists.
  s,

  /// 48dp — list rows, the default.
  m,

  /// 72dp — profile headers.
  l,
}

/// A cast member avatar with initial fallback, identity ring, and online dot.
///
/// Covers the Content/Avatar row of `components.md`
/// (`size S/M/L + 캐스트 컬러 링 + 출근중 점`). When [imageProvider] is null it
/// falls back to the member's initials on the assigned hue's pastel surface
/// (text uses that hue's ink — tokens.md §1). The optional [hue] paints an
/// identity ring (응원색 culture, references #11); [isOnline] adds a matcha
/// "출근중" dot.
class AssenAvatar extends StatelessWidget {
  /// Creates an avatar for [name] (used to derive the initial fallback).
  ///
  /// Provide [imageProvider] for a photo; omit it to show initials. [hue] tints
  /// the identity ring and the fallback surface; [isOnline] shows the on-shift
  /// dot.
  const AssenAvatar({
    required this.name,
    this.imageProvider,
    this.semanticLabel,
    this.size = AssenAvatarSize.m,
    this.hue,
    this.isOnline = false,
    super.key,
  });

  /// The cast member's name. The first character drives the initial fallback.
  final String name;

  /// Optional avatar image. When null, initials are shown instead.
  final ImageProvider<Object>? imageProvider;

  /// Optional screen-reader description for the photo (e.g. "미오 프로필 사진").
  ///
  /// Domain-agnostic: the host passes the label so no product wording is
  /// hard-coded here. Applied only when [imageProvider] is set — the initials
  /// fallback is already announced as its letter.
  final String? semanticLabel;

  /// Avatar diameter bucket — see [AssenAvatarSize].
  final AssenAvatarSize size;

  /// Optional cast identity hue. When set, draws a coloured ring and tints the
  /// initial-fallback surface.
  final AssenBadgeHue? hue;

  /// Whether to show the "출근중" (on-shift) dot.
  final bool isOnline;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final diameter = _diameter;
    final ringColor = hue == null ? null : _ringColor(colors);

    Widget avatar = Container(
      width: diameter,
      height: diameter,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _fallbackBg(colors),
        image: imageProvider == null
            ? null
            : DecorationImage(image: imageProvider!, fit: BoxFit.cover),
        border: ringColor == null
            ? null
            : Border.all(color: ringColor, width: 2),
      ),
      alignment: Alignment.center,
      child: imageProvider != null ? null : _initials(colors),
    );

    if (isOnline) {
      avatar = Stack(
        clipBehavior: Clip.none,
        children: [
          avatar,
          Positioned(
            right: 0,
            bottom: 0,
            child: Container(
              width: _dotSize,
              height: _dotSize,
              decoration: BoxDecoration(
                color: colors.mintInk,
                shape: BoxShape.circle,
                border: Border.all(color: colors.white, width: 2),
              ),
            ),
          ),
        ],
      );
    }

    if (imageProvider != null && semanticLabel != null) {
      return Semantics(image: true, label: semanticLabel, child: avatar);
    }
    return avatar;
  }

  Widget _initials(AssenColors colors) {
    final initial = name.isEmpty ? '?' : name.characters.first;
    return Text(
      initial,
      style: TextStyle(
        color: _fallbackInk(colors),
        fontSize: _diameter * 0.4,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  double get _diameter => switch (size) {
    AssenAvatarSize.s => SpacingTokens.s8,
    AssenAvatarSize.m => SpacingTokens.s12,
    AssenAvatarSize.l => 72,
  };

  double get _dotSize => switch (size) {
    AssenAvatarSize.s => SpacingTokens.s2,
    AssenAvatarSize.m => SpacingTokens.s3,
    AssenAvatarSize.l => SpacingTokens.s4,
  };

  Color _fallbackBg(AssenColors c) {
    if (hue == null) return c.indigo100;
    return switch (hue!) {
      AssenBadgeHue.brand => c.indigo100,
      AssenBadgeHue.peach => c.violetBg,
      AssenBadgeHue.lemon => c.creamBg,
      AssenBadgeHue.matcha => c.mintBg,
      AssenBadgeHue.sky => c.skyBg,
      AssenBadgeHue.lavender => c.lavenderBg,
    };
  }

  Color _fallbackInk(AssenColors c) {
    if (hue == null) return c.indigoInk;
    return switch (hue!) {
      AssenBadgeHue.brand => c.indigoInk,
      AssenBadgeHue.peach => c.violetInk,
      AssenBadgeHue.lemon => c.creamInk,
      AssenBadgeHue.matcha => c.mintInk,
      AssenBadgeHue.sky => c.skyInk,
      AssenBadgeHue.lavender => c.lavenderInk,
    };
  }

  Color _ringColor(AssenColors c) {
    return switch (hue!) {
      AssenBadgeHue.brand => c.indigoInk,
      AssenBadgeHue.peach => c.violetInk,
      AssenBadgeHue.lemon => c.creamInk,
      AssenBadgeHue.matcha => c.mintInk,
      AssenBadgeHue.sky => c.skyInk,
      AssenBadgeHue.lavender => c.lavenderInk,
    };
  }
}
