import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/templates/cast_profile_template.dart';
import 'package:ui_kit/src/templates/cheki_album_template.dart';
import 'package:ui_kit/src/templates/event_template.dart';
import 'package:ui_kit/src/templates/home_template.dart';
import 'package:ui_kit/src/templates/operator_dashboard_template.dart';
import 'package:ui_kit/src/templates/points_history_template.dart';
import 'package:ui_kit/src/templates/schedule_template.dart';

/// A single-screen index of every Template for visual review.
///
/// The human-facing review surface for the ASS-88 Templates layer: it lists all
/// templates (T1–T5 plus fan event C4/C5 additions) as cards that open the
/// full-screen template — the same review
/// pattern as `AtomCatalog`/`MoleculeCatalog`/`OrganismCatalog`, adapted because
/// templates are whole screens (own Scaffold/AppBar) rather than inline widgets.
/// Opening each entry exercises that template's real chrome and scroll.
class TemplateCatalog extends StatelessWidget {
  /// Creates the template catalogue index screen.
  const TemplateCatalog({super.key});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AppBar(
        title: const Text('Templates'),
        backgroundColor: colors.cream100,
        foregroundColor: colors.ink900,
      ),
      body: ListView(
        padding: const EdgeInsets.all(SpacingTokens.screenMargin),
        children: [
          _TemplateEntry(
            title: 'T1 홈 (회원증)',
            summary: '회원증 + 스탬프 + 오늘의 출근 + 이벤트 + 탭바',
            builder: (_) => const AssenHomeTemplate(),
          ),
          _TemplateEntry(
            title: 'T2 출근표',
            summary: '주간 출근표 + 최애 필터 + 캐스트 슬롯',
            builder: (_) => const AssenScheduleTemplate(),
          ),
          _TemplateEntry(
            title: 'T3 캐스트 프로필',
            summary: '프로필 헤더 + 출근 일정 + 체키 컬렉션 + 예약 CTA',
            builder: (_) => const AssenCastProfileTemplate(),
          ),
          _TemplateEntry(
            title: 'T4 체키 앨범 (채움)',
            summary: '수집 진행 + 체키 그리드 + 미수집 셀',
            builder: (_) => const AssenChekiAlbumTemplate(),
          ),
          _TemplateEntry(
            title: 'T4 체키 앨범 (빈 상태)',
            summary: 'EmptyState 변형 — 수집 0건',
            builder: (_) => const AssenChekiAlbumTemplate(
              variant: AssenChekiAlbumVariant.empty,
            ),
          ),
          _TemplateEntry(
            title: 'C4 이벤트 목록',
            summary: '필터 탭 + 시즌 배너 + 이벤트 상태 카드',
            builder: (_) => const AssenEventListTemplate(
              events: _catalogEvents,
              onEventTap: _noopEventTap,
            ),
          ),
          _TemplateEntry(
            title: 'C5 이벤트 상세',
            summary: '히어로 + 배지 + 상세 정보 + 예약 CTA',
            builder: (_) => const AssenEventDetailTemplate(
              event: _catalogMioBirthdayEvent,
              onBack: _noopBack,
            ),
          ),
          _TemplateEntry(
            title: 'F3 포인트 내역',
            summary: '보유 포인트 요약 + 월별 적립/사용 타임라인',
            builder: (_) => const AssenPointsHistoryTemplate(
              summary: AssenPointsSummary(
                balance: 1250,
                expiryNote: '이번 달 소멸 예정 없음',
              ),
              monthGroups: _catalogPointGroups,
              onBack: _noopBack,
            ),
          ),
          _TemplateEntry(
            title: 'T5 운영자 대시보드',
            summary: '신고 알림 + 세그먼트 탭 + 지표 그리드 + 예약/대기 보드',
            builder: (_) => const AssenOperatorDashboardTemplate(),
          ),
        ],
      ),
    );
  }
}

void _noopBack() {}

void _noopEventTap(String id) {}

const AssenFanEvent _catalogMioBirthdayEvent = AssenFanEvent(
  id: 'mio-birthday-week',
  title: '미오 생탄제',
  meta: '6.14 (토) · 한정 메뉴 · 특별 체키',
  status: AssenFanEventStatus.upcoming,
  category: AssenFanEventCategory.cast,
  statusLabel: 'D-3',
  actionLabel: '예약 가능',
  hue: AssenBadgeHue.lemon,
  relatedCast: '미오',
  schedule: '6월 14일 (토) 13:00–21:00',
  participation: '예약 후 매장 방문',
  benefit: '생탄제 한정 체키 + 포토카드',
);

const List<AssenFanEvent> _catalogEvents = [
  _catalogMioBirthdayEvent,
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

const List<AssenPointsMonthGroup> _catalogPointGroups = [
  AssenPointsMonthGroup(
    monthLabel: '6월',
    entries: [
      AssenPointEntry(
        title: '12번째 방문 적립',
        dateLabel: '6월 11일 (수)',
        delta: 50,
      ),
      AssenPointEntry(
        title: '생탄제 이벤트 보너스',
        dateLabel: '6월 8일 (일)',
        delta: 200,
      ),
      AssenPointEntry(
        title: '포인트로 결제',
        dateLabel: '6월 4일 (수)',
        delta: -500,
      ),
    ],
  ),
  AssenPointsMonthGroup(
    monthLabel: '5월',
    entries: [
      AssenPointEntry(
        title: '11번째 방문 적립',
        dateLabel: '5월 28일 (수)',
        delta: 50,
      ),
    ],
  ),
];

/// A tappable catalogue row that opens a full-screen template.
class _TemplateEntry extends StatelessWidget {
  const _TemplateEntry({
    required this.title,
    required this.summary,
    required this.builder,
  });

  final String title;
  final String summary;
  final WidgetBuilder builder;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s3),
      child: AssenCard(
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(builder: builder),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: TypographyTokens.titleMSize,
                      fontWeight: FontWeight.w700,
                      color: colors.ink900,
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.s1),
                  Text(
                    summary,
                    style: TextStyle(
                      fontSize: TypographyTokens.labelSize,
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
      ),
    );
  }
}
