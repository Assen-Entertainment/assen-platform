import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/atoms/progress.dart';
import 'package:ui_kit/src/molecules/cheki_frame.dart';
import 'package:ui_kit/src/molecules/collection_cell.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/empty_state.dart';

/// Which state the [AssenChekiAlbumTemplate] renders.
enum AssenChekiAlbumVariant {
  /// 채움 — the collected grid with a progress count.
  filled,

  /// 빈 — the empty album (an [AssenEmptyState] in place of the grid).
  empty,
}

/// A single owned cheki entry in the album grid (image motif + caption).
class AssenChekiEntry {
  /// Creates a cheki entry.
  const AssenChekiEntry({required this.caption, this.hue});

  /// The caption shown in the frame's lower band.
  final String caption;

  /// The pastel motif hue for the photo window (a cast identity colour).
  final AssenBadgeHue? hue;
}

/// The cheki album screen skeleton (`T4 체키 앨범`).
///
/// Covers the Templates/T4 row of `components.md` and the 체키 앨범 screen
/// (screens.md E1). It assembles an [AssenAppBar], a 수집 진행 header (a 도감
/// count over an [AssenProgressBar]), and — per [variant] — either the
/// collected grid ([AssenChekiFrame]s, which double as album cells) followed by
/// the still-locked [AssenCollectionCell]s, or the [AssenEmptyState] for a fan
/// who has not collected any cheki yet.
///
/// Content is placeholder data (fictional cast frames), surfaced as constructor
/// parameters so a real screen overrides it (screens.md mock rule).
class AssenChekiAlbumTemplate extends StatelessWidget {
  /// Creates the cheki album template.
  ///
  /// [variant] picks the filled grid or the empty state. [entries] are the
  /// owned cheki; [collected]/[total] drive the 도감 count and progress bar.
  /// [lockedCount] adds that many locked silhouette cells after the owned
  /// frames. The `on*` callbacks are optional (the gallery passes no-ops).
  const AssenChekiAlbumTemplate({
    this.variant = AssenChekiAlbumVariant.filled,
    this.entries = _defaultEntries,
    this.collected = 6,
    this.total = 12,
    this.lockedCount = 3,
    this.onBack,
    this.onExplore,
    super.key,
  });

  /// The album render variant — filled grid or empty state.
  final AssenChekiAlbumVariant variant;

  /// The owned cheki entries shown as frames.
  final List<AssenChekiEntry> entries;

  /// The number of collected cheki (the 도감 numerator).
  final int collected;

  /// The total collectible cheki (the 도감 denominator).
  final int total;

  /// How many locked silhouette cells trail the owned frames.
  final int lockedCount;

  /// Optional back handler.
  final VoidCallback? onBack;

  /// Optional "explore casts" handler (the empty-state CTA).
  final VoidCallback? onExplore;

  /// The unified placeholder owned-cheki set (fictional cast frames).
  static const List<AssenChekiEntry> _defaultEntries = [
    AssenChekiEntry(caption: '미오 · 첫 방문', hue: AssenBadgeHue.strawberry),
    AssenChekiEntry(caption: '유키 · 6월', hue: AssenBadgeHue.sky),
    AssenChekiEntry(caption: '모카 · 디저트', hue: AssenBadgeHue.peach),
    AssenChekiEntry(caption: '베리 · 게임', hue: AssenBadgeHue.lavender),
    AssenChekiEntry(caption: '미오 · 콜라보', hue: AssenBadgeHue.strawberry),
    AssenChekiEntry(caption: '유키 · 한정', hue: AssenBadgeHue.sky),
  ];

  bool get _isEmpty => variant == AssenChekiAlbumVariant.empty;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: '체키 앨범',
        onBack: onBack,
        actions: [
          AssenIconButton(
            icon: Icons.shuffle,
            semanticLabel: '섞어 보기',
            onPressed: () {},
          ),
        ],
      ),
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s4,
              SpacingTokens.screenMargin,
              SpacingTokens.s8,
            ),
            sliver: SliverList.list(
              children: [
                _ProgressHeader(
                  collected: _isEmpty ? 0 : collected,
                  total: total,
                ),
                const SizedBox(height: SpacingTokens.s6),
                if (_isEmpty)
                  _EmptyAlbum(onExplore: onExplore)
                else
                  _AlbumGrid(
                    entries: entries,
                    lockedCount: lockedCount,
                    colors: colors,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The 수집 진행 header: a 도감 count over the progress bar.
class _ProgressHeader extends StatelessWidget {
  const _ProgressHeader({required this.collected, required this.total});

  final int collected;
  final int total;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final value = total == 0 ? 0.0 : collected / total;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '도감',
              style: TextStyle(
                fontSize: TypographyTokens.labelSize,
                fontWeight: FontWeight.w700,
                color: colors.ink900,
              ),
            ),
            Text(
              '$collected / $total',
              style: TextStyle(
                fontSize: TypographyTokens.labelSize,
                fontWeight: FontWeight.w700,
                color: colors.strawberryInk,
              ),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.s3),
        AssenProgressBar(value: value),
      ],
    );
  }
}

/// The collected-cheki grid: owned frames followed by locked silhouettes.
class _AlbumGrid extends StatelessWidget {
  const _AlbumGrid({
    required this.entries,
    required this.lockedCount,
    required this.colors,
  });

  final List<AssenChekiEntry> entries;
  final int lockedCount;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    final owned = entries.length;
    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: SpacingTokens.s4,
        crossAxisSpacing: SpacingTokens.s3,
        // The instax frame is taller than wide (54×86 film ratio).
        childAspectRatio: 54 / 86,
      ),
      itemCount: owned + lockedCount,
      itemBuilder: (context, index) {
        if (index < owned) {
          final entry = entries[index];
          return AssenChekiFrame(
            caption: entry.caption,
            onTap: () {},
            image: ColoredBox(color: _hueBg(colors, entry.hue)),
          );
        }
        return const AssenCollectionCell(
          artwork: SizedBox.shrink(),
          label: '미수집',
          state: AssenCollectionState.locked,
        );
      },
    );
  }

  Color _hueBg(AssenColors c, AssenBadgeHue? hue) {
    return switch (hue) {
      AssenBadgeHue.strawberry => c.strawberryBg,
      AssenBadgeHue.peach => c.peachBg,
      AssenBadgeHue.lemon => c.lemonBg,
      AssenBadgeHue.matcha => c.matchaBg,
      AssenBadgeHue.sky => c.skyBg,
      AssenBadgeHue.lavender => c.lavenderBg,
      null => c.strawberryBg,
    };
  }
}

/// The empty-album state shown when no cheki has been collected.
class _EmptyAlbum extends StatelessWidget {
  const _EmptyAlbum({required this.onExplore});

  final VoidCallback? onExplore;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return AssenEmptyState(
      title: '아직 모은 체키가 없어요',
      message: '방문하고 체키를 받으면 이곳에 모여요.',
      slot: Container(
        width: SpacingTokens.s16,
        height: SpacingTokens.s16,
        decoration: BoxDecoration(
          color: colors.strawberryBg,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(
          Icons.photo_library_outlined,
          size: SpacingTokens.s8,
          color: colors.strawberryInk,
        ),
      ),
      actionLabel: '캐스트 보러 가기',
      onAction: onExplore ?? () {},
    );
  }
}
