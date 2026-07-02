import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

final Provider<List<AssenFanEvent>> _fanEventsProvider =
    Provider<List<AssenFanEvent>>((ref) => _mockEvents);

/// Fan-facing event list screen (C4).
///
/// It keeps C4 on local fictional data until the event API lands, while the
/// shared ui_kit template owns only the visual states and filter behavior.
///
/// Below the large desktop class (<1200dp) it renders the unchanged stacked
/// [AssenEventListTemplate] and tapping a card pushes `/events/:id` (mobile
/// flow, byte-for-byte as before). At large and wider it becomes a Material 3
/// list-detail (ASS-147 Slice 3): a responsive event feed beside a detail pane
/// that mounts the chrome-less [AssenEventDetailBody] for the selected event,
/// so a desktop browser fills the surface. The route push is retained for
/// deep-links and back. Selection lives in screen-local state — this is an
/// out-of-shell route, so leaving and re-entering disposes/recreates the screen
/// and the detail pane resets (no app-global provider, no stale selection).
class EventListScreen extends ConsumerStatefulWidget {
  /// Creates the event list screen.
  const EventListScreen({super.key});

  @override
  ConsumerState<EventListScreen> createState() => _EventListScreenState();
}

class _EventListScreenState extends ConsumerState<EventListScreen> {
  static const List<String> _tabs = ['전체', '캐스트', '이벤트', '공지'];

  int _selectedTab = 0;
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    final events = ref.watch(_fanEventsProvider);

    return LayoutBuilder(
      builder: (context, constraints) {
        // Gate on the width the list-detail scaffold will actually receive
        // (after the screen-margin padding), so the screen and the scaffold
        // agree on the breakpoint. Gating on the raw width would open a dead
        // band just above 1200dp where the screen enters the wide path but the
        // padded scaffold collapses to list-only, leaving a card tap with
        // nowhere to go (no push, no pane).
        final contentWidth =
            constraints.maxWidth - SpacingTokens.screenMargin * 2;
        final wide = AssenWindowSize.fromWidth(
          contentWidth,
        ).atLeast(AssenWindowSize.large);

        // Mobile / tablet: unchanged single-column list; the template owns its
        // own filter state and tapping a card pushes the detail route.
        if (!wide) {
          return AssenEventListTemplate(
            events: events,
            onEventTap: (id) => context.push(FanRoutes.eventPath(id)),
            onBack: () => _pop(context),
          );
        }

        return _buildWide(context, events);
      },
    );
  }

  Widget _buildWide(BuildContext context, List<AssenFanEvent> events) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final visible = _filteredEvents(events);
    final selected = _resolveSelected(visible);

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(title: '하츠코이', onBack: () => _pop(context)),
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
                const SizedBox(height: SpacingTokens.s6),
                const AssenSectionHeader(title: '이벤트'),
                const SizedBox(height: SpacingTokens.s4),
                AssenListDetailScaffold(
                  // breakpoint defaults to large; the outer LayoutBuilder above
                  // already gates the whole wide path at >= large.
                  list: AssenFeedGrid(
                    maxColumns: 2,
                    children: [
                      for (final event in visible)
                        _EventGridCard(
                          event: event,
                          selected: event.id == selected?.id,
                          onTap: () => setState(() => _selectedId = event.id),
                        ),
                    ],
                  ),
                  detail: selected == null
                      ? const AssenEmptyState(
                          title: '이벤트를 선택해 주세요',
                          message: '왼쪽 목록에서 이벤트를 고르면 상세가 여기에 표시돼요.',
                        )
                      : AssenEventDetailBody(
                          key: ValueKey(selected.id),
                          event: selected,
                          onClose: () => setState(() => _selectedId = null),
                          onReserve:
                              selected.status == AssenFanEventStatus.ended
                              ? null
                              : () => context.go(FanRoutes.reservation),
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  List<AssenFanEvent> _filteredEvents(List<AssenFanEvent> events) {
    return switch (_selectedTab) {
      1 =>
        events
            .where((event) => event.category == AssenFanEventCategory.cast)
            .toList(),
      2 =>
        events
            .where((event) => event.category == AssenFanEventCategory.event)
            .toList(),
      3 =>
        events
            .where((event) => event.category == AssenFanEventCategory.notice)
            .toList(),
      _ => events,
    };
  }

  // Resolve the selection against the currently visible (filtered) events so
  // the detail pane always corresponds to a card on screen; a filter that hides
  // the selected event falls back to the empty-state prompt.
  AssenFanEvent? _resolveSelected(List<AssenFanEvent> visible) {
    if (_selectedId == null) return null;
    for (final event in visible) {
      if (event.id == _selectedId) return event;
    }
    return null;
  }

  void _pop(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(FanRoutes.home);
    }
  }
}

/// A selectable event card for the wide list-detail feed (ASS-147 Slice 3).
///
/// Tapping selects the event (the host populates the detail pane) rather than
/// pushing a route — the desktop list-detail keeps the user on `/events`. The
/// selection ring is the only visual difference from the stacked card.
class _EventGridCard extends StatelessWidget {
  const _EventGridCard({
    required this.event,
    required this.selected,
    required this.onTap,
  });

  final AssenFanEvent event;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final active = event.status != AssenFanEventStatus.ended;

    // InkWell (not a bare GestureDetector) so the desktop list cards are
    // keyboard-focusable and activatable (Enter/Space) and traverse in the
    // feed's row-major order; Semantics carries the selected state for AT.
    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        color: colors.white,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.lg)),
        child: InkWell(
          onTap: onTap,
          borderRadius: const BorderRadius.all(
            Radius.circular(RadiusTokens.lg),
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(
                color: selected ? colors.roseMain : colors.ink100,
                width: selected ? 2 : 1,
              ),
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
                      AssenBadge(
                        label: event.statusLabel,
                        hue: switch (event.status) {
                          AssenFanEventStatus.upcoming => AssenBadgeHue.lemon,
                          AssenFanEventStatus.ongoing => AssenBadgeHue.matcha,
                          AssenFanEventStatus.ended => AssenBadgeHue.sky,
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: SpacingTokens.s2),
                  Text(
                    event.meta,
                    style: TypographyTokens.bodyM.copyWith(
                      color: colors.ink700,
                    ),
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
}

/// Fan-facing event detail screen (C5).
///
/// The CTA routes to the existing reservation tab only for active event states;
/// no reservation or pricing logic is introduced here.
class EventDetailScreen extends ConsumerWidget {
  /// Creates an event detail screen for the route [eventId].
  const EventDetailScreen({required this.eventId, super.key});

  /// Event id from `/events/:id`.
  final String eventId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final event = ref.watch(
      _fanEventsProvider.select((events) => _findEventById(events, eventId)),
    );

    if (event == null) {
      final colors = Theme.of(context).extension<AssenColors>()!;

      return Scaffold(
        backgroundColor: colors.cream50,
        appBar: AssenAppBar(
          title: '이벤트',
          onBack: () => context.go(FanRoutes.events),
        ),
        body: AssenEmptyState(
          title: '이벤트를 찾을 수 없어요',
          message: '이벤트 목록에서 다시 확인해 주세요.',
          actionLabel: '이벤트 목록 보기',
          onAction: () => context.go(FanRoutes.events),
        ),
      );
    }

    return AssenEventDetailTemplate(
      event: event,
      onBack: () => _pop(context),
      onReserve: event.status == AssenFanEventStatus.ended
          ? null
          : () => context.go(FanRoutes.reservation),
    );
  }

  void _pop(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(FanRoutes.events);
    }
  }
}

AssenFanEvent? _findEventById(List<AssenFanEvent> events, String eventId) {
  for (final event in events) {
    if (event.id == eventId) return event;
  }
  return null;
}

const List<AssenFanEvent> _mockEvents = [
  AssenFanEvent(
    id: 'mio-birthday-week',
    title: '미오 생탄제',
    meta: '6.14 (일) · 한정 메뉴 · 특별 체키',
    status: AssenFanEventStatus.upcoming,
    category: AssenFanEventCategory.cast,
    statusLabel: 'D-3',
    actionLabel: '예약 가능',
    hue: AssenBadgeHue.lemon,
    relatedCast: '미오',
    schedule: '6월 14일 (일) 13:00–21:00',
    participation: '예약 후 매장 방문',
    benefit: '생탄제 한정 체키 + 포토카드',
  ),
  AssenFanEvent(
    id: 'strawberry-season',
    title: '딸기 시즌 — 신메뉴 위크',
    meta: '6.1–6.30 · 시즌 한정 메뉴 3종',
    status: AssenFanEventStatus.ongoing,
    category: AssenFanEventCategory.event,
    statusLabel: '진행중',
    actionLabel: '오늘 참여',
    hue: AssenBadgeHue.matcha,
    relatedCast: '유키',
    schedule: '6월 1일 (월) 13:00–21:00',
    participation: '매장 방문 후 직원 안내',
    benefit: '시즌 한정 체키 + 스탬프',
  ),
  AssenFanEvent(
    id: 'parents-day-tea-party',
    title: '5월 어버이날 티 파티',
    meta: '5월 · 사진 공개',
    status: AssenFanEventStatus.ended,
    category: AssenFanEventCategory.notice,
    statusLabel: '종료',
    actionLabel: '종료됨',
    hue: AssenBadgeHue.sky,
    relatedCast: '미오',
    schedule: '5월 8일 (금) 13:00–21:00',
    participation: '현장 참여',
    benefit: '기념 포토카드',
  ),
];
