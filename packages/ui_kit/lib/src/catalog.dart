import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/button.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/atoms/chips.dart';
import 'package:ui_kit/src/atoms/divider.dart';
import 'package:ui_kit/src/atoms/favorite_button.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/atoms/progress.dart';
import 'package:ui_kit/src/atoms/selection_controls.dart';
import 'package:ui_kit/src/atoms/skeleton.dart';

/// A single-screen gallery of every Atom for visual review.
///
/// This is the human-facing review surface for ASS-88: it renders all 18 atoms
/// (each in its relevant variants) on the cream surface so reviewers and the
/// `flutter build web` smoke test exercise the whole catalogue at once. It is
/// stateful so interactive atoms (toggles, chips, selection controls) actually
/// respond in the gallery.
class AtomCatalog extends StatefulWidget {
  /// Creates the atom catalogue screen.
  const AtomCatalog({super.key});

  @override
  State<AtomCatalog> createState() => _AtomCatalogState();
}

class _AtomCatalogState extends State<AtomCatalog> {
  bool _checkbox = true;
  bool _switch = true;
  bool _favorite = true;
  int _radio = 0;
  int _page = 0;
  final Set<String> _filters = {'체키'};
  AssenTimeSlotState _slot = AssenTimeSlotState.available;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AppBar(
        title: const Text('Atoms'),
        backgroundColor: colors.cream100,
        foregroundColor: colors.ink900,
      ),
      body: ListView(
        padding: const EdgeInsets.all(SpacingTokens.screenMargin),
        children: [
          _Section(
            title: 'Button',
            child: Wrap(
              spacing: SpacingTokens.s2,
              runSpacing: SpacingTokens.s2,
              children: [
                AssenButton(label: '예약하기', onPressed: () {}),
                AssenButton(
                  label: '둘러보기',
                  style: AssenButtonStyle.secondary,
                  onPressed: () {},
                ),
                AssenButton(
                  label: '취소',
                  style: AssenButtonStyle.ghost,
                  onPressed: () {},
                ),
                const AssenButton(label: '비활성', onPressed: null),
              ],
            ),
          ),
          _Section(
            title: 'Button (expand — bottom CTA)',
            child: AssenButton(
              label: '하단 고정 CTA',
              expand: true,
              icon: Icons.check_circle_outline,
              onPressed: () {},
            ),
          ),
          _Section(
            title: 'IconButton · FavoriteButton',
            child: Row(
              children: [
                AssenIconButton(
                  icon: Icons.close,
                  semanticLabel: '닫기',
                  onPressed: () {},
                ),
                AssenIconButton(
                  icon: Icons.share_outlined,
                  semanticLabel: '공유',
                  onPressed: () {},
                ),
                const AssenIconButton(
                  icon: Icons.settings_outlined,
                  semanticLabel: '설정',
                  onPressed: null,
                ),
                AssenFavoriteButton(
                  isFavorite: _favorite,
                  onChanged: (v) => setState(() => _favorite = v),
                ),
              ],
            ),
          ),
          _Section(
            title: 'Checkbox · Radio · Switch',
            child: Row(
              children: [
                AssenCheckbox(
                  value: _checkbox,
                  onChanged: (v) => setState(() => _checkbox = v),
                ),
                const AssenCheckbox(value: false, onChanged: null),
                AssenRadio<int>(
                  value: 0,
                  groupValue: _radio,
                  onChanged: (v) => setState(() => _radio = v),
                ),
                AssenRadio<int>(
                  value: 1,
                  groupValue: _radio,
                  onChanged: (v) => setState(() => _radio = v),
                ),
                AssenSwitch(
                  value: _switch,
                  onChanged: (v) => setState(() => _switch = v),
                ),
                const AssenSwitch(value: false, onChanged: null),
              ],
            ),
          ),
          _Section(
            title: 'FilterChip',
            child: Wrap(
              spacing: SpacingTokens.s2,
              children: [
                for (final f in const ['체키', '게임', '이벤트'])
                  AssenFilterChip(
                    label: f,
                    selected: _filters.contains(f),
                    count: f == '체키' ? 12 : null,
                    onSelected: (sel) => setState(() {
                      if (sel) {
                        _filters.add(f);
                      } else {
                        _filters.remove(f);
                      }
                    }),
                  ),
              ],
            ),
          ),
          _Section(
            title: 'TimeSlotChip',
            child: Wrap(
              spacing: SpacingTokens.s2,
              children: [
                AssenTimeSlotChip(
                  label: '14:00',
                  state: _slot == AssenTimeSlotState.selected
                      ? AssenTimeSlotState.selected
                      : AssenTimeSlotState.available,
                  onTap: () =>
                      setState(() => _slot = AssenTimeSlotState.selected),
                ),
                const AssenTimeSlotChip(
                  label: '15:00',
                  state: AssenTimeSlotState.full,
                  onTap: null,
                ),
              ],
            ),
          ),
          _Section(
            title: 'Badge (6 hues)',
            child: Wrap(
              spacing: SpacingTokens.s2,
              runSpacing: SpacingTokens.s2,
              children: [
                for (final hue in AssenBadgeHue.values)
                  AssenBadge(label: hue.name, hue: hue),
              ],
            ),
          ),
          const _Section(
            title: 'CountBadge · StatusBadge',
            child: Wrap(
              spacing: SpacingTokens.s2,
              runSpacing: SpacingTokens.s2,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                AssenCountBadge(count: 3),
                AssenCountBadge(count: 128),
                AssenCountBadge(count: 0),
                AssenStatusBadge(
                  kind: AssenStatusKind.confirmed,
                  label: '확정',
                ),
                AssenStatusBadge(kind: AssenStatusKind.pending, label: '대기'),
                AssenStatusBadge(kind: AssenStatusKind.done, label: '완료'),
                AssenStatusBadge(
                  kind: AssenStatusKind.cancelled,
                  label: '취소',
                ),
              ],
            ),
          ),
          const _Section(
            title: 'Avatar (S/M/L · hue ring · 출근중)',
            child: Row(
              children: [
                AssenAvatar(name: '하나', size: AssenAvatarSize.s),
                AssenAvatar(name: '미오', hue: AssenBadgeHue.sky),
                SizedBox(width: SpacingTokens.s2),
                AssenAvatar(
                  name: '리코',
                  size: AssenAvatarSize.l,
                  hue: AssenBadgeHue.lavender,
                  isOnline: true,
                ),
              ],
            ),
          ),
          const _Section(title: 'Divider', child: AssenDivider()),
          _Section(
            title: 'ProgressBar · ProgressDonut',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const AssenProgressBar(value: 0.4),
                const SizedBox(height: SpacingTokens.s4),
                AssenProgressDonut(
                  value: 0.625,
                  center: Text(
                    '5/8',
                    style: TextStyle(
                      color: colors.ink900,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          _Section(
            title: 'PageIndicator',
            child: GestureDetector(
              onTap: () => setState(() => _page = (_page + 1) % 4),
              child: AssenPageIndicator(count: 4, activeIndex: _page),
            ),
          ),
          const _Section(
            title: 'Skeleton',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AssenSkeleton(width: 180),
                SizedBox(height: SpacingTokens.s2),
                AssenSkeleton(width: 120),
              ],
            ),
          ),
          _Section(
            title: 'Card (level0 · level1)',
            child: Column(
              children: [
                AssenCard(
                  child: Text(
                    'level0 — 보더',
                    style: TextStyle(color: colors.ink900),
                  ),
                ),
                const SizedBox(height: SpacingTokens.s3),
                AssenCard(
                  level: AssenCardLevel.level1,
                  onTap: () {},
                  child: Text(
                    'level1 — 그림자 (탭 가능)',
                    style: TextStyle(color: colors.ink900),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A labelled block grouping one atom's variants in the catalogue.
class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TypographyTokens.label.copyWith(
              color: colors.ink700,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: SpacingTokens.s3),
          child,
        ],
      ),
    );
  }
}
