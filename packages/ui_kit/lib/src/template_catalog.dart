import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/card.dart';
import 'package:ui_kit/src/templates/cast_profile_template.dart';
import 'package:ui_kit/src/templates/cheki_album_template.dart';
import 'package:ui_kit/src/templates/home_template.dart';
import 'package:ui_kit/src/templates/operator_dashboard_template.dart';
import 'package:ui_kit/src/templates/schedule_template.dart';

/// A single-screen index of every Template for visual review.
///
/// The human-facing review surface for the ASS-88 Templates layer: it lists all
/// five templates (T1–T5, including T4's filled/empty variants and T5's tab
/// states) as cards that open the full-screen template — the same review
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
            title: 'T5 운영자 대시보드',
            summary: '신고 알림 + 세그먼트 탭 + 지표 그리드 + 예약/대기 보드',
            builder: (_) => const AssenOperatorDashboardTemplate(),
          ),
        ],
      ),
    );
  }
}

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
