import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/card.dart';

// Typography sizes are literals until TypographyTokens lands.
// TODO(ASS-130): replace with TypographyTokens (tokens.md §3).
const double _reportTitleSize = 14; // tokens.md §3 body.m — entry title
const double _reportSubSize = 12; // tokens.md §3 body.s — entry description
const double _reportTypeSize = 14; // tokens.md §3 body.m — type row label

/// The nine safety report types (`유형 9종`).
///
/// The fixed taxonomy a reporter chooses from (components.md Domain/
/// SafetyReportEntry, screens.md F5). Each maps to a label and a glyph; the set
/// is closed so the same categories surface across the fan and cast apps.
enum AssenSafetyReportType {
  /// 성희롱·성추행.
  harassment,

  /// 폭언·모욕.
  abusiveLanguage,

  /// 스토킹·따라다님.
  stalking,

  /// 강요·갈취.
  coercion,

  /// 사생활 침해·촬영.
  privacy,

  /// 폭력·위협.
  violence,

  /// 차별·혐오 발언.
  discrimination,

  /// 규정 위반·부정 행위.
  ruleViolation,

  /// 기타.
  other,
}

/// The Korean label for an [AssenSafetyReportType].
extension AssenSafetyReportTypeLabel on AssenSafetyReportType {
  /// The human-readable report-type label.
  String get label => switch (this) {
    AssenSafetyReportType.harassment => '성희롱·성추행',
    AssenSafetyReportType.abusiveLanguage => '폭언·모욕',
    AssenSafetyReportType.stalking => '스토킹·따라다님',
    AssenSafetyReportType.coercion => '강요·갈취',
    AssenSafetyReportType.privacy => '사생활 침해·촬영',
    AssenSafetyReportType.violence => '폭력·위협',
    AssenSafetyReportType.discrimination => '차별·혐오 발언',
    AssenSafetyReportType.ruleViolation => '규정 위반·부정 행위',
    AssenSafetyReportType.other => '기타',
  };

  /// The leading glyph for the report type.
  IconData get icon => switch (this) {
    AssenSafetyReportType.harassment => Icons.report_gmailerrorred_outlined,
    AssenSafetyReportType.abusiveLanguage => Icons.sms_failed_outlined,
    AssenSafetyReportType.stalking => Icons.directions_walk_outlined,
    AssenSafetyReportType.coercion => Icons.pan_tool_outlined,
    AssenSafetyReportType.privacy => Icons.no_photography_outlined,
    AssenSafetyReportType.violence => Icons.dangerous_outlined,
    AssenSafetyReportType.discrimination => Icons.do_not_disturb_on_outlined,
    AssenSafetyReportType.ruleViolation => Icons.gavel_outlined,
    AssenSafetyReportType.other => Icons.more_horiz,
  };
}

/// The always-visible safety report entry (`신고 진입 셀 — 상시 노출`).
///
/// Covers the Domain/SafetyReportEntry row of `components.md`. A persistent
/// entry the fan and cast apps surface on every screen (screens.md F5), opening
/// the report flow. It is a tappable [AssenCard] with a sky-pastel shield mark,
/// a title and a reassuring subtitle — calm, neutral framing (no alarming red;
/// red is reserved for destructive confirms, tokens.md §1). Pair it with
/// [AssenSafetyReportTypeList] to pick one of the nine report types.
class AssenSafetyReportEntry extends StatelessWidget {
  /// Creates a safety report entry cell.
  ///
  /// [title]/[subtitle] are the entry copy; [onTap] opens the report flow.
  const AssenSafetyReportEntry({
    required this.onTap,
    this.title = '안전 신고하기',
    this.subtitle = '불편하거나 위험한 상황을 알려 주세요. 접수 내용은 안전하게 보호됩니다.',
    super.key,
  });

  /// The entry title.
  final String title;

  /// The reassuring entry description.
  final String subtitle;

  /// Opens the report flow.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenCard(
      onTap: onTap,
      child: Row(
        children: [
          Container(
            width: SpacingTokens.s10,
            height: SpacingTokens.s10,
            decoration: BoxDecoration(
              color: colors.skyBg,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              Icons.shield_outlined,
              color: colors.skyInk,
              size: SpacingTokens.s5,
            ),
          ),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: _reportTitleSize,
                    fontWeight: FontWeight.w700,
                    color: colors.ink900,
                  ),
                ),
                const SizedBox(height: SpacingTokens.s1),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontSize: _reportSubSize,
                    height: 1.4,
                    color: colors.ink700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: SpacingTokens.s2),
          Icon(Icons.chevron_right, color: colors.ink300),
        ],
      ),
    );
  }
}

/// The nine-type report selector list (`유형 9종 선택`).
///
/// Renders every [AssenSafetyReportType] as a selectable row (icon + label +
/// chevron). The currently picked type, if any, is highlighted with the sky
/// surface. Reports the chosen type via [onSelect]. Typically hosted in an
/// `AssenBottomSheet` (Korean B2C convention #2 — pick in a bottom sheet).
class AssenSafetyReportTypeList extends StatelessWidget {
  /// Creates the report-type selector.
  ///
  /// [selected] highlights the active type (or null for none). [onSelect]
  /// reports a tapped type.
  const AssenSafetyReportTypeList({
    required this.onSelect,
    this.selected,
    super.key,
  });

  /// The currently selected type, or null.
  final AssenSafetyReportType? selected;

  /// Reports a tapped report type.
  final ValueChanged<AssenSafetyReportType> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final type in AssenSafetyReportType.values)
          _TypeRow(
            type: type,
            isSelected: type == selected,
            colors: colors,
            onTap: () => onSelect(type),
          ),
      ],
    );
  }
}

/// A single report-type row.
class _TypeRow extends StatelessWidget {
  const _TypeRow({
    required this.type,
    required this.isSelected,
    required this.colors,
    required this.onTap,
  });

  final AssenSafetyReportType type;
  final bool isSelected;
  final AssenColors colors;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: isSelected,
      label: type.label,
      child: InkWell(
        onTap: onTap,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.s3,
            vertical: SpacingTokens.s3,
          ),
          decoration: BoxDecoration(
            color: isSelected ? colors.skyBg : Colors.transparent,
            borderRadius: const BorderRadius.all(
              Radius.circular(RadiusTokens.md),
            ),
          ),
          child: Row(
            children: [
              Icon(
                type.icon,
                size: SpacingTokens.s5,
                color: isSelected ? colors.skyInk : colors.ink700,
              ),
              const SizedBox(width: SpacingTokens.s3),
              Expanded(
                child: Text(
                  type.label,
                  style: TextStyle(
                    fontSize: _reportTypeSize,
                    fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                    color: colors.ink900,
                  ),
                ),
              ),
              if (isSelected)
                Icon(Icons.check, size: SpacingTokens.s5, color: colors.skyInk),
            ],
          ),
        ),
      ),
    );
  }
}
