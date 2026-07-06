import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/molecules/agreement_cell.dart';
import 'package:ui_kit/src/molecules/banner_card.dart';
import 'package:ui_kit/src/molecules/key_value_row.dart';
import 'package:ui_kit/src/molecules/list_item.dart';
import 'package:ui_kit/src/molecules/notice_bar.dart';
import 'package:ui_kit/src/molecules/otp_field.dart';
import 'package:ui_kit/src/molecules/search_field.dart';
import 'package:ui_kit/src/molecules/section_header.dart';
import 'package:ui_kit/src/molecules/segmented_tabs.dart';
import 'package:ui_kit/src/molecules/stat_card.dart';
import 'package:ui_kit/src/molecules/stat_row.dart';
import 'package:ui_kit/src/molecules/step_indicator.dart';
import 'package:ui_kit/src/molecules/stepper.dart';
import 'package:ui_kit/src/molecules/text_field.dart';
import 'package:ui_kit/src/molecules/timeline_item.dart';
import 'package:ui_kit/src/molecules/toast.dart';
import 'package:ui_kit/src/molecules/underline_tabs.dart';

/// A single-screen gallery of every Molecule for visual review.
///
/// The human-facing review surface for the ASS-88 Molecules layer: it renders
/// all 16 molecules (each in its relevant variants/states) on the cream surface
/// so reviewers and the `flutter build web` smoke test exercise the whole layer
/// at once — the same pattern as `AtomCatalog`. It is stateful so interactive
/// molecules (fields, steppers, tabs, toggles) actually respond in the gallery.
class MoleculeCatalog extends StatefulWidget {
  /// Creates the molecule catalogue screen.
  const MoleculeCatalog({super.key});

  @override
  State<MoleculeCatalog> createState() => _MoleculeCatalogState();
}

class _MoleculeCatalogState extends State<MoleculeCatalog> {
  final TextEditingController _search = TextEditingController(text: '미오');
  int _party = 2;
  bool _agreeAll = false;
  bool _agreeRequired = true;
  int _segment = 0;
  int _tab = 1;

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AppBar(
        title: const Text('Molecules'),
        backgroundColor: colors.cream100,
        foregroundColor: colors.ink900,
      ),
      body: ListView(
        padding: const EdgeInsets.all(SpacingTokens.screenMargin),
        children: [
          const _Section(
            title: 'TextField (default · error · disabled)',
            child: Column(
              children: [
                AssenTextField(label: '이름', hintText: '실명을 입력하세요'),
                SizedBox(height: SpacingTokens.s3),
                AssenTextField(
                  label: '이메일',
                  errorText: '이메일 형식이 올바르지 않습니다',
                ),
                SizedBox(height: SpacingTokens.s3),
                AssenTextField(label: '비활성', enabled: false),
              ],
            ),
          ),
          _Section(
            title: 'SearchField',
            child: AssenSearchField(controller: _search),
          ),
          _Section(
            title: 'OTPField (입력중)',
            child: AssenOtpField(onChanged: (_) {}),
          ),
          _Section(
            title: 'Stepper (예약 인원)',
            child: AssenStepper(
              value: _party,
              semanticLabel: '인원',
              onChanged: (v) => setState(() => _party = v),
            ),
          ),
          _Section(
            title: 'AgreementCell (전체동의 + 필수/선택)',
            child: Column(
              children: [
                AssenAgreementCell(
                  label: '전체 동의',
                  kind: AssenAgreementKind.all,
                  value: _agreeAll,
                  onChanged: (v) => setState(() => _agreeAll = v),
                ),
                AssenAgreementCell(
                  label: '서비스 이용약관 동의',
                  value: _agreeRequired,
                  onViewTerms: () {},
                  onChanged: (v) => setState(() => _agreeRequired = v),
                ),
                AssenAgreementCell(
                  label: '마케팅 정보 수신 동의',
                  kind: AssenAgreementKind.optional,
                  value: false,
                  onViewTerms: () {},
                  onChanged: (_) {},
                ),
              ],
            ),
          ),
          _Section(
            title: 'ListItem (slots)',
            child: Column(
              children: [
                AssenListItem(
                  title: '내 회원증',
                  subtitle: '하츠코이 본점',
                  leading: const AssenAvatar(name: '미오'),
                  onTap: () {},
                ),
                AssenListItem(
                  title: '알림 설정',
                  trailing: const AssenBadge(label: 'NEW'),
                  onTap: () {},
                ),
              ],
            ),
          ),
          const _Section(
            title: 'KeyValueRow (기본 · 강조)',
            child: Column(
              children: [
                AssenKeyValueRow(label: '메뉴', value: '오므라이스'),
                AssenKeyValueRow(
                  label: '결제 금액',
                  value: '₩12,000',
                  emphasis: true,
                ),
              ],
            ),
          ),
          _Section(
            title: 'SectionHeader (액션 유)',
            child: AssenSectionHeader(
              title: '획득한 체키',
              actionLabel: '전체보기',
              onAction: () {},
            ),
          ),
          const _Section(
            title: 'StatRow (프로필 지표)',
            child: AssenStatRow(
              stats: [
                AssenStat(value: '1,284', label: '팔로워'),
                AssenStat(value: '37', label: '게시물'),
              ],
            ),
          ),
          const _Section(
            title: 'NoticeBar (info · warning)',
            child: Column(
              children: [
                AssenNoticeBar(message: '오늘은 11:00에 문을 엽니다.'),
                SizedBox(height: SpacingTokens.s2),
                AssenNoticeBar(
                  message: '예약 마감이 임박했습니다.',
                  kind: AssenNoticeKind.warning,
                ),
              ],
            ),
          ),
          const _Section(
            title: 'Toast (성공 · 오류 · 정보)',
            child: Column(
              children: [
                AssenToast(
                  message: '예약이 완료되었습니다.',
                  kind: AssenToastKind.success,
                ),
                SizedBox(height: SpacingTokens.s2),
                AssenToast(
                  message: '잠시 후 다시 시도해 주세요.',
                  kind: AssenToastKind.error,
                ),
                SizedBox(height: SpacingTokens.s2),
                AssenToast(message: '광고성 알림 수신 설정이 변경되었습니다.'),
              ],
            ),
          ),
          _Section(
            title: 'SegmentedTabs (운영자 화면)',
            child: AssenSegmentedTabs(
              segments: const ['대기', '예약'],
              selectedIndex: _segment,
              onChanged: (i) => setState(() => _segment = i),
            ),
          ),
          _Section(
            title: 'UnderlineTabs (가로 스크롤)',
            child: AssenUnderlineTabs(
              tabs: const ['전체', '체키', '이벤트', '게임', '콜라보'],
              selectedIndex: _tab,
              onChanged: (i) => setState(() => _tab = i),
            ),
          ),
          _Section(
            title: 'StepIndicator (본인인증)',
            child: AssenStepIndicator(
              count: 4,
              currentStep: 2,
              labels: const ['약관', '통신사', '번호', 'OTP'],
            ),
          ),
          const _Section(
            title: 'TimelineItem (방문 이력)',
            child: Column(
              children: [
                AssenTimelineItem(
                  date: '2026.06.10',
                  title: '12번째 방문',
                  subtitle: '만난 캐스트: 미오, 리코',
                  isFirst: true,
                ),
                AssenTimelineItem(
                  date: '2026.05.28',
                  title: '11번째 방문',
                  subtitle: '만난 캐스트: 하나',
                  isLast: true,
                ),
              ],
            ),
          ),
          _Section(
            title: 'BannerCard (이벤트 배너)',
            child: AssenBannerCard(
              title: '6월 콜라보 이벤트',
              subtitle: '한정 체키 증정',
              background: ColoredBox(color: colors.lavenderBg),
              onTap: () {},
            ),
          ),
          const _Section(
            title: 'StatCard (운영자 지표)',
            child: Row(
              children: [
                Expanded(
                  child: AssenStatCard(
                    value: '1,284',
                    label: '오늘 방문',
                    delta: '+12%',
                    trend: AssenStatTrend.up,
                    icon: Icons.people_outline,
                  ),
                ),
                SizedBox(width: SpacingTokens.s3),
                Expanded(
                  child: AssenStatCard(
                    value: '37',
                    label: '대기 인원',
                    delta: '-4',
                    trend: AssenStatTrend.down,
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

/// A labelled block grouping one molecule's variants in the catalogue.
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
