import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/selection_controls.dart';

/// A consent row variant — master "agree to all" vs. a single required/optional
/// item (Korean B2C convention #3: 전체동의 셀 + [필수]/[선택] 개별행).
enum AssenAgreementKind {
  /// 전체 동의 — the master row whose checkbox toggles every item at once.
  all,

  /// [필수] — a legally required consent; the form cannot proceed without it.
  required,

  /// [선택] — an optional consent the user may decline.
  optional,
}

/// A single agreement (consent) row (`전체동의 / [필수] / [선택]`).
///
/// Covers the Inputs/AgreementCell row of `components.md` and the Korean B2C
/// convention #3 (약관 = 전체동의 셀 + 필수/선택 개별행 + 전문 화살표). Composes an
/// [AssenCheckbox] with the row label and, for individual rows, a [필수]/[선택]
/// tag and a "전문 보기" chevron ([onViewTerms]). The [AssenAgreementKind.all]
/// row reads in a heavier weight so it stands apart as the master toggle.
///
/// This molecule is intentionally just the *cell*: stacking the master + items
/// and the all/none toggle logic belongs to the form (an Organism), per the
/// task scope (molecules are cells/fields only).
class AssenAgreementCell extends StatelessWidget {
  /// Creates a consent row labelled [label] of the given [kind].
  ///
  /// [value] is the checkbox state and [onChanged] toggles it (null disables).
  /// [onViewTerms], when set on an individual row, shows a trailing chevron
  /// that opens the full terms; the master ([AssenAgreementKind.all]) row omits
  /// it.
  const AssenAgreementCell({
    required this.label,
    required this.value,
    required this.onChanged,
    this.kind = AssenAgreementKind.required,
    this.onViewTerms,
    super.key,
  });

  /// The consent text (e.g. "서비스 이용약관 동의").
  final String label;

  /// Whether this consent is checked.
  final bool value;

  /// Toggles the checkbox; null disables the row.
  final ValueChanged<bool>? onChanged;

  /// Which consent variant this row is — see [AssenAgreementKind].
  final AssenAgreementKind kind;

  /// Opens the full terms text. Ignored for the master
  /// ([AssenAgreementKind.all] renders no chevron).
  final VoidCallback? onViewTerms;

  bool get _isAll => kind == AssenAgreementKind.all;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return InkWell(
      onTap: onChanged == null ? null : () => onChanged!(!value),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s1),
        child: Row(
          children: [
            AssenCheckbox(value: value, onChanged: onChanged),
            if (!_isAll) ...[
              _Tag(
                required: kind == AssenAgreementKind.required,
                colors: colors,
              ),
              const SizedBox(width: SpacingTokens.s2),
            ],
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: _isAll
                      ? TypographyTokens.titleMSize
                      : TypographyTokens.bodyMSize,
                  fontWeight: _isAll ? FontWeight.w700 : FontWeight.w500,
                  color: colors.ink900,
                ),
              ),
            ),
            if (!_isAll && onViewTerms != null)
              IconButton(
                icon: Icon(Icons.chevron_right, color: colors.ink500),
                tooltip: '$label 전문 보기',
                onPressed: onViewTerms,
              ),
          ],
        ),
      ),
    );
  }
}

/// The `[필수]` / `[선택]` prefix tag. Required uses the indigo ink (it gates the
/// form); optional uses the muted ink ramp.
class _Tag extends StatelessWidget {
  const _Tag({required this.required, required this.colors});

  final bool required;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Text(
      required ? '[필수]' : '[선택]',
      style: TextStyle(
        fontSize: TypographyTokens.bodySSize,
        fontWeight: FontWeight.w700,
        color: required ? colors.indigo500 : colors.ink500,
      ),
    );
  }
}
