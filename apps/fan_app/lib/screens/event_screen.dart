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
class EventListScreen extends ConsumerWidget {
  /// Creates the event list screen.
  const EventListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final events = ref.watch(_fanEventsProvider);

    return AssenEventListTemplate(
      events: events,
      onEventTap: (id) => context.push(FanRoutes.eventPath(id)),
      onBack: () => _pop(context),
    );
  }

  void _pop(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go(FanRoutes.home);
    }
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
