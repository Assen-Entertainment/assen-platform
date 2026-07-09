import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';

/// A pill-shaped search input (`default / focused`).
///
/// Covers the Inputs/SearchField row of `components.md`. Unlike the multi-line
/// text field it is a single rounded (`radius.full`) field with a search glyph
/// a clear (✕) affordance once there is text — the standard list/collection
/// search affordance. The resting border is the ink ramp; focus thickens it to
/// the indigo action anchor. Solid fills only (tokens.md — no gradient).
class AssenSearchField extends StatelessWidget {
  /// Creates a search field.
  ///
  /// [onChanged] fires on every edit; [onClear] (when provided) is invoked by
  /// the trailing clear button, which appears only while [controller] has text.
  /// [hintText] defaults to a neutral "검색" placeholder.
  const AssenSearchField({
    required this.controller,
    this.hintText = '검색',
    this.onChanged,
    this.onSubmitted,
    this.onClear,
    super.key,
  });

  /// Controller owning the query text (required so the clear button can read
  /// emptiness without a stateful wrapper).
  final TextEditingController controller;

  /// Placeholder shown when the query is empty.
  final String hintText;

  /// Called on every edit with the current query.
  final ValueChanged<String>? onChanged;

  /// Called when the user submits the query from the keyboard.
  final ValueChanged<String>? onSubmitted;

  /// Called when the clear (✕) button is tapped. The field's text is also
  /// cleared by this widget before the callback runs.
  final VoidCallback? onClear;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    OutlineInputBorder border(Color color, {double width = 1}) {
      return OutlineInputBorder(
        borderRadius: const BorderRadius.all(
          Radius.circular(RadiusTokens.full),
        ),
        borderSide: BorderSide(color: color, width: width),
      );
    }

    // Rebuild the trailing affordance when text presence changes.
    return ValueListenableBuilder<TextEditingValue>(
      valueListenable: controller,
      builder: (context, value, _) {
        final hasText = value.text.isNotEmpty;
        return TextField(
          controller: controller,
          onChanged: onChanged,
          onSubmitted: onSubmitted,
          textInputAction: TextInputAction.search,
          style: TextStyle(
            fontSize: TypographyTokens.bodyLSize,
            color: colors.ink900,
          ),
          cursorColor: colors.indigo500,
          decoration: InputDecoration(
            hintText: hintText,
            hintStyle: TextStyle(
              fontSize: TypographyTokens.bodyLSize,
              color: colors.ink500,
            ),
            prefixIcon: Icon(Icons.search, color: colors.ink500),
            suffixIcon: hasText
                ? IconButton(
                    icon: Icon(Icons.close, color: colors.ink500),
                    tooltip: '지우기',
                    onPressed: () {
                      controller.clear();
                      onClear?.call();
                    },
                  )
                : null,
            filled: true,
            fillColor: colors.neutral100,
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: SpacingTokens.s4,
              vertical: SpacingTokens.s3,
            ),
            enabledBorder: border(colors.neutral200),
            focusedBorder: border(colors.indigo500, width: 2),
          ),
        );
      },
    );
  }
}
