import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/button.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/molecules/banner_card.dart';
import 'package:ui_kit/src/molecules/key_value_row.dart';
import 'package:ui_kit/src/molecules/notice_bar.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/molecules/underline_tabs.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/bottom_cta.dart';

/// Fan event lifecycle states used by C4/C5.
///
/// The enum lives in ui_kit because status changes visual treatment across both
/// list cards and detail CTAs, while the app still owns event data and routing.
enum AssenFanEventStatus {
  /// Future event with a countdown badge and active reservation affordance.
  upcoming,

  /// Currently running event with an active participation affordance.
  ongoing,

  /// Finished event, rendered muted with no active reservation CTA.
  ended,
}

/// Fan event category filter used by the visual tab row.
///
/// Keeping categories typed prevents app screens from comparing display labels
/// when filtering local mock data.
enum AssenFanEventCategory {
  /// Cast-related event.
  cast,

  /// Shop event.
  event,

  /// Announcement.
  notice,
}

/// Display data for a fan-facing event card and detail page.
///
/// The app supplies already approved copy so the template only decides layout,
/// token colours, and status affordances.
class AssenFanEvent {
  /// Creates event display data for the C4/C5 templates.
  const AssenFanEvent({
    required this.id,
    required this.title,
    required this.meta,
    required this.status,
    required this.category,
    required this.statusLabel,
    required this.actionLabel,
    required this.hue,
    required this.relatedCast,
    required this.schedule,
    required this.participation,
    required this.benefit,
  });

  /// Stable app-owned id used for detail navigation.
  final String id;

  /// Event title shown on cards and the detail hero.
  final String title;

  /// Compact period/context line for the list card.
  final String meta;

  /// Lifecycle state that controls active or muted affordances.
  final AssenFanEventStatus status;

  /// Category used by the list filter tabs.
  final AssenFanEventCategory category;

  /// Badge text such as `D-3`, `진행중`, or `종료`.
  final String statusLabel;

  /// Card action label such as `예약 가능`.
  final String actionLabel;

  /// Pastel hue for the event surface.
  final AssenBadgeHue hue;

  /// Related fictional cast label shown on the detail badge row.
  final String relatedCast;

  /// Detail schedule row value.
  final String schedule;

  /// Detail participation-method row value.
  final String participation;

  /// Detail benefit row value.
  final String benefit;
}

/// Fan event list template (C4).
///
/// The template owns the AppBar, visual tabs, seasonal banner, and token-based
/// card states; filtering state stays local because C4 is a client-side mock
/// surface until the backend contract exists.
class AssenEventListTemplate extends StatefulWidget {
  /// Creates the C4 event list template.
  const AssenEventListTemplate({
    required this.events,
    required this.onEventTap,
    this.onBack,
    super.key,
  });

  /// Events available to the client-side filters.
  final List<AssenFanEvent> events;

  /// Called when an event card is opened.
  final ValueChanged<String> onEventTap;

  /// Optional back handler for pushed event-list routes.
  final VoidCallback? onBack;

  @override
  State<AssenEventListTemplate> createState() => _AssenEventListTemplateState();
}

class _AssenEventListTemplateState extends State<AssenEventListTemplate> {
  static const List<String> _tabs = ['전체', '캐스트', '이벤트', '공지'];

  int _selectedTab = 0;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final visibleEvents = _filteredEvents();

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '하츠코이', onBack: widget.onBack),
      body: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(
              SpacingTokens.screenMargin,
              SpacingTokens.s3,
              SpacingTokens.screenMargin,
              SpacingTokens.s8,
            ),
            sliver: SliverList.list(
              children: [
                AssenUnderlineTabs(
                  tabs: _tabs,
                  selectedIndex: _selectedTab,
                  onChanged: (index) => setState(() => _selectedTab = index),
                ),
                const SizedBox(height: SpacingTokens.s4),
                AssenBannerCard(
                  title: '6월 생탄제 — 미오 생일 위크',
                  subtitle: '6.14–6.20 · 한정 메뉴와 특별 체키',
                  aspectRatio: 2,
                  background: SizedBox(
                    width: SpacingTokens.s16,
                    height: SpacingTokens.s16,
                    child: ColoredBox(color: colors.lavenderBg),
                  ),
                ),
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '이벤트'),
                const SizedBox(height: SpacingTokens.s3),
                for (var i = 0; i < visibleEvents.length; i++) ...[
                  _FanEventCard(
                    event: visibleEvents[i],
                    onTap: () => widget.onEventTap(visibleEvents[i].id),
                  ),
                  if (i != visibleEvents.length - 1)
                    const SizedBox(height: SpacingTokens.s3),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<AssenFanEvent> _filteredEvents() {
    return switch (_selectedTab) {
      1 =>
        widget.events
            .where((event) => event.category == AssenFanEventCategory.cast)
            .toList(),
      2 =>
        widget.events
            .where((event) => event.category == AssenFanEventCategory.event)
            .toList(),
      3 =>
        widget.events
            .where((event) => event.category == AssenFanEventCategory.notice)
            .toList(),
      _ => widget.events,
    };
  }
}

/// Fan event detail template (C5).
///
/// Detail copy is deliberately structured as key-value rows so future backend
/// fields can replace the mock provider without changing the visual contract.
class AssenEventDetailTemplate extends StatelessWidget {
  /// Creates the C5 event detail template for [event].
  const AssenEventDetailTemplate({
    required this.event,
    required this.onBack,
    this.onReserve,
    super.key,
  });

  /// Event data to render.
  final AssenFanEvent event;

  /// Back affordance handler.
  final VoidCallback onBack;

  /// Reservation route handler; omitted for ended events.
  final VoidCallback? onReserve;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final active = event.status != AssenFanEventStatus.ended;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '이벤트', onBack: onBack),
      bottomNavigationBar: active
          ? AssenBottomCta(
              primaryLabel: '이 날짜로 예약하기',
              onPrimary: onReserve,
            )
          : null,
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
                _EventHero(event: event),
                const SizedBox(height: SpacingTokens.s4),
                Wrap(
                  spacing: SpacingTokens.s2,
                  runSpacing: SpacingTokens.s2,
                  children: [
                    _statusBadge(event),
                    AssenBadge(
                      label: event.relatedCast,
                      hue: AssenBadgeHue.lavender,
                    ),
                  ],
                ),
                const SizedBox(height: SpacingTokens.s4),
                AssenCard(
                  child: Column(
                    children: [
                      AssenKeyValueRow(label: '일정', value: event.schedule),
                      AssenKeyValueRow(
                        label: '참여 방법',
                        value: event.participation,
                      ),
                      AssenKeyValueRow(label: '특전', value: event.benefit),
                    ],
                  ),
                ),
                const SizedBox(height: SpacingTokens.s4),
                const AssenNoticeBar(
                  kind: AssenNoticeKind.warning,
                  message: '당일 예약 변경은 매장으로 문의해 주세요',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  AssenBadge _statusBadge(AssenFanEvent event) => _eventStatusBadge(event);
}

/// The Scaffold-less event detail body for embedding in a list-detail pane
/// (ASS-147 Slice 3, Rec 1 pane-embed contract).
///
/// Renders the same content as [AssenEventDetailTemplate] (hero, badges,
/// key-value card, notice) but WITHOUT a [Scaffold], [AssenAppBar], or
/// [AssenBottomCta], so it mounts cleanly inside a detail pane that already
/// lives under the surrounding screen's chrome — no nested app bar or bottom
/// CTA. Its affordances act on the PANE, not the route: [onClose] clears the
/// host's selection (it must NOT pop the route), and [onReserve] is the host's
/// pane-supplied reserve action. The reserve affordance is an inline
/// [AssenButton] (not an [AssenBottomCta]) shown only for active events.
///
/// The route-built full-Scaffold path ([AssenEventDetailTemplate]) is unchanged
/// and stays the only thing `/events/:id` builds on push and on cold deep-link.
class AssenEventDetailBody extends StatelessWidget {
  /// Creates an embeddable event detail body for [event].
  const AssenEventDetailBody({
    required this.event,
    this.onReserve,
    this.onClose,
    super.key,
  });

  /// Event data to render.
  final AssenFanEvent event;

  /// Pane-supplied reserve action; omitted (or for ended events) hides the
  /// inline reserve button. Acts on the host, not on global navigation.
  final VoidCallback? onReserve;

  /// Clears the host's pane selection. MUST act on the pane (e.g. set the
  /// selected id to null), never `context.pop()` the surrounding route.
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    final active = event.status != AssenFanEventStatus.ended;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (onClose != null)
          Align(
            alignment: Alignment.centerRight,
            child: AssenIconButton(
              icon: Icons.close,
              semanticLabel: '상세 닫기',
              onPressed: onClose,
            ),
          ),
        _EventHero(event: event),
        const SizedBox(height: SpacingTokens.s4),
        Wrap(
          spacing: SpacingTokens.s2,
          runSpacing: SpacingTokens.s2,
          children: [
            _eventStatusBadge(event),
            AssenBadge(label: event.relatedCast, hue: AssenBadgeHue.lavender),
          ],
        ),
        const SizedBox(height: SpacingTokens.s4),
        AssenCard(
          child: Column(
            children: [
              AssenKeyValueRow(label: '일정', value: event.schedule),
              AssenKeyValueRow(label: '참여 방법', value: event.participation),
              AssenKeyValueRow(label: '특전', value: event.benefit),
            ],
          ),
        ),
        const SizedBox(height: SpacingTokens.s4),
        const AssenNoticeBar(
          kind: AssenNoticeKind.warning,
          message: '당일 예약 변경은 매장으로 문의해 주세요',
        ),
        if (active && onReserve != null) ...[
          const SizedBox(height: SpacingTokens.s5),
          AssenButton(
            label: '이 날짜로 예약하기',
            onPressed: onReserve,
            expand: true,
          ),
        ],
      ],
    );
  }
}

/// The status badge shared by the event card, detail template, and detail body.
AssenBadge _eventStatusBadge(AssenFanEvent event) => AssenBadge(
  label: event.statusLabel,
  hue: switch (event.status) {
    AssenFanEventStatus.upcoming => AssenBadgeHue.lemon,
    AssenFanEventStatus.ongoing => AssenBadgeHue.matcha,
    AssenFanEventStatus.ended => AssenBadgeHue.sky,
  },
);

class _FanEventCard extends StatelessWidget {
  const _FanEventCard({required this.event, required this.onTap});

  final AssenFanEvent event;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final active = event.status != AssenFanEventStatus.ended;
    final (background, foreground, border) = _eventPalette(colors, event.hue);

    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: AssenCard(
          padding: EdgeInsets.zero,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: background,
              border: Border.all(color: border),
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.lg),
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.all(SpacingTokens.s4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          event.title,
                          style: TypographyTokens.titleL.copyWith(
                            color: colors.ink900,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      const SizedBox(width: SpacingTokens.s2),
                      _statusBadge(event),
                    ],
                  ),
                  const SizedBox(height: SpacingTokens.s2),
                  Text(
                    event.meta,
                    style: TypographyTokens.bodyM.copyWith(color: foreground),
                  ),
                  const SizedBox(height: SpacingTokens.s4),
                  Align(
                    alignment: Alignment.centerRight,
                    child: Text(
                      event.actionLabel,
                      style: TypographyTokens.label.copyWith(
                        color: active ? colors.roseMain : colors.ink500,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  AssenBadge _statusBadge(AssenFanEvent event) => _eventStatusBadge(event);
}

class _EventHero extends StatelessWidget {
  const _EventHero({required this.event});

  final AssenFanEvent event;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final (background, foreground, border) = _eventPalette(colors, event.hue);

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.s6),
      decoration: BoxDecoration(
        color: background,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        border: Border.all(color: border),
      ),
      child: Stack(
        children: [
          Positioned(
            right: SpacingTokens.s2,
            top: SpacingTokens.s1,
            child: _DecorativeDot(color: foreground),
          ),
          Positioned(
            right: SpacingTokens.s8,
            bottom: SpacingTokens.s2,
            child: _DecorativeDot(color: foreground, small: true),
          ),
          Padding(
            padding: const EdgeInsets.only(right: SpacingTokens.s10),
            child: Text(
              event.title,
              style: TypographyTokens.headline.copyWith(
                color: colors.ink900,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DecorativeDot extends StatelessWidget {
  const _DecorativeDot({required this.color, this.small = false});

  final Color color;
  final bool small;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: small ? SpacingTokens.s3 : SpacingTokens.s5,
      height: small ? SpacingTokens.s3 : SpacingTokens.s5,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

(Color, Color, Color) _eventPalette(AssenColors colors, AssenBadgeHue hue) {
  return switch (hue) {
    AssenBadgeHue.strawberry => (
      colors.strawberryBgSubtle,
      colors.strawberryInk,
      colors.strawberryBorder,
    ),
    AssenBadgeHue.peach => (
      colors.peachBgSubtle,
      colors.peachInk,
      colors.peachBorder,
    ),
    AssenBadgeHue.lemon => (
      colors.lemonBgSubtle,
      colors.lemonInk,
      colors.lemonBorder,
    ),
    AssenBadgeHue.matcha => (
      colors.matchaBgSubtle,
      colors.matchaInk,
      colors.matchaBorder,
    ),
    AssenBadgeHue.sky => (
      colors.skyBgSubtle,
      colors.skyInk,
      colors.skyBorder,
    ),
    AssenBadgeHue.lavender => (
      colors.lavenderBgSubtle,
      colors.lavenderInk,
      colors.lavenderBorder,
    ),
  };
}
