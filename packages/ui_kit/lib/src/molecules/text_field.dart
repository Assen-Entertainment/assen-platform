import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// The single-line text input (`default / focused / error / disabled`).
///
/// Covers the Inputs/TextField row of `components.md` and replaces the
/// deprecated `InputField`. Composes Flutter's [TextField] with the design
/// system's ink ramp and rose action anchor: the border is the ink ramp at
/// rest, the rose anchor when focused, and `red.main` when [errorText] is set.
/// Disabled (`enabled: false`) mutes to the ink ramp — it never goes darker
/// than the resting state (tokens.md §1 disabled = muted, not darker).
///
/// Accessibility: a visible [label] is always rendered (never placeholder-only,
/// which fails screen readers and vanishes on input); the 44pt touch floor is
/// inherited from the Material input height plus content padding.
class AssenTextField extends StatelessWidget {
  /// Creates a text field labelled [label].
  ///
  /// [errorText], when non-null, switches the field to its error styling and
  /// shows the message. `enabled: false` renders the disabled state.
  /// [controller] is optional for callers that own the text state.
  const AssenTextField({
    required this.label,
    this.controller,
    this.hintText,
    this.errorText,
    this.helperText,
    this.onChanged,
    this.keyboardType,
    this.obscureText = false,
    this.enabled = true,
    this.prefixIcon,
    super.key,
  });

  /// The always-visible field label (accessibility — never placeholder-only).
  final String label;

  /// Optional external text controller.
  final TextEditingController? controller;

  /// Optional placeholder shown inside the empty field.
  final String? hintText;

  /// When non-null, the field renders in its error state with this message.
  final String? errorText;

  /// Optional helper text shown below the field when there is no [errorText].
  final String? helperText;

  /// Called on every edit with the current text.
  final ValueChanged<String>? onChanged;

  /// Optional keyboard type (e.g. [TextInputType.emailAddress]).
  final TextInputType? keyboardType;

  /// Whether to obscure input (passwords).
  final bool obscureText;

  /// Whether the field is interactive. `false` renders the disabled state.
  final bool enabled;

  /// Optional leading glyph (e.g. a person icon on a name field).
  final IconData? prefixIcon;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final hasError = errorText != null;

    OutlineInputBorder border(Color color, {double width = 1}) {
      return OutlineInputBorder(
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        borderSide: BorderSide(color: color, width: width),
      );
    }

    return TextField(
      controller: controller,
      enabled: enabled,
      onChanged: onChanged,
      keyboardType: keyboardType,
      obscureText: obscureText,
      style: TextStyle(
        fontSize: TypographyTokens.bodyLSize,
        color: enabled ? colors.ink900 : colors.ink500,
      ),
      cursorColor: colors.roseMain,
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        helperText: helperText,
        errorText: errorText,
        prefixIcon: prefixIcon == null ? null : Icon(prefixIcon),
        filled: true,
        fillColor: enabled ? colors.white : colors.cream200,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.s4,
          vertical: SpacingTokens.s3,
        ),
        labelStyle: TextStyle(
          fontSize: TypographyTokens.labelSize,
          color: hasError ? colors.redInk : colors.ink700,
        ),
        floatingLabelStyle: TextStyle(
          color: hasError ? colors.redMain : colors.roseMain,
        ),
        hintStyle: TextStyle(
          fontSize: TypographyTokens.bodyLSize,
          color: colors.ink500,
        ),
        helperStyle: TextStyle(
          fontSize: TypographyTokens.bodySSize,
          color: colors.ink500,
        ),
        errorStyle: TextStyle(
          fontSize: TypographyTokens.bodySSize,
          color: colors.redMain,
        ),
        enabledBorder: border(hasError ? colors.redMain : colors.ink200),
        focusedBorder: border(
          hasError ? colors.redMain : colors.roseMain,
          width: 2,
        ),
        errorBorder: border(colors.redMain),
        focusedErrorBorder: border(colors.redMain, width: 2),
        disabledBorder: border(colors.ink100),
      ),
    );
  }
}
