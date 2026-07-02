import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/bottom_cta.dart';
import 'package:ui_kit/src/organisms/cast_profile_card.dart';
import 'package:ui_kit/src/organisms/empty_state.dart';
import 'package:ui_kit/src/organisms/error_state.dart';
import 'package:ui_kit/src/organisms/event_card.dart';
import 'package:ui_kit/src/organisms/membership_card.dart';
import 'package:ui_kit/src/organisms/qr_display.dart';
import 'package:ui_kit/src/organisms/reservation_card.dart';
import 'package:ui_kit/src/organisms/safety_report_entry.dart';
import 'package:ui_kit/src/organisms/schedule_calendar.dart';
import 'package:ui_kit/src/organisms/stamp_card.dart';

/// A single-screen gallery of every Organism for visual review.
///
/// The human-facing review surface for the ASS-88 Organisms layer: it renders
/// all 15 organisms (each in its relevant variants/states) on the cream surface
/// so reviewers and the `flutter build web` smoke test exercise the whole layer
/// at once — the same pattern as `AtomCatalog`/`MoleculeCatalog`. It is stateful
/// so interactive organisms (tab bar, schedule, report picker) respond live.
/// AppBar, TabBar, BottomCTA, BottomSheet and Dialog also frame this screen so
/// the navigation organisms are exercised in their real chrome roles.
class OrganismCatalog extends StatefulWidget {
  /// Creates the organism catalogue screen.
  const OrganismCatalog({super.key});

  @override
  State<OrganismCatalog> createState() => _OrganismCatalogState();
}

class _OrganismCatalogState extends State<OrganismCatalog> {
  int _tab = 0;
  int _scheduleDay = 2;
  AssenSafetyReportType? _reportType = AssenSafetyReportType.harassment;
  bool _favorite = true;

  static const List<AssenScheduleDay> _week = [
    AssenScheduleDay(
      weekday: '월',
      day: 9,
      casts: [
        AssenScheduleCast(
          name: '미오',
          shift: '12:00–18:00',
          hue: AssenBadgeHue.strawberry,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '화', day: 10, isClosed: true),
    AssenScheduleDay(
      weekday: '수',
      day: 11,
      hasEvent: true,
      casts: [
        AssenScheduleCast(
          name: '유키',
          shift: '13:00–19:00',
          hue: AssenBadgeHue.sky,
        ),
        AssenScheduleCast(
          name: '모카',
          shift: '16:00–22:00',
          hue: AssenBadgeHue.peach,
        ),
      ],
    ),
    AssenScheduleDay(
      weekday: '목',
      day: 12,
      casts: [
        AssenScheduleCast(
          name: '베리',
          shift: '12:00–18:00',
          hue: AssenBadgeHue.lavender,
        ),
      ],
    ),
    AssenScheduleDay(weekday: '금', day: 13, hasEvent: true),
    AssenScheduleDay(weekday: '토', day: 14),
    AssenScheduleDay(weekday: '일', day: 15, isClosed: true),
  ];

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Scaffold(
      backgroundColor: colors.cream50,
      appBar: AssenAppBar(
        title: 'Organisms',
        onBack: () {},
        actions: [
          AssenIconButton(
            icon: Icons.notifications_none,
            semanticLabel: '알림',
            onPressed: () {},
          ),
        ],
      ),
      bottomNavigationBar: AssenTabBar(
        currentIndex: _tab,
        onChanged: (i) => setState(() => _tab = i),
        items: const [
          AssenTabItem(
            icon: Icons.home_outlined,
            activeIcon: Icons.home,
            label: '홈',
          ),
          AssenTabItem(icon: Icons.calendar_month_outlined, label: '출근표'),
          AssenTabItem(icon: Icons.event_outlined, label: '예약'),
          AssenTabItem(
            icon: Icons.photo_library_outlined,
            label: '체키',
            badgeCount: 3,
          ),
          AssenTabItem(icon: Icons.person_outline, label: '마이'),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(SpacingTokens.screenMargin),
        children: [
          _Section(
            title: 'MembershipCard (간판 — strawberry/sky/lavender skin)',
            child: Column(
              children: [
                AssenMembershipCard(
                  name: '미오',
                  memberNumber: '0000 1234 5678',
                  points: '1,280',
                  tierLabel: '하츠코이',
                  avatar: const AssenAvatar(
                    name: '미오',
                    hue: AssenBadgeHue.strawberry,
                  ),
                  onShowQr: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                const AssenMembershipCard(
                  name: '유키',
                  memberNumber: '0000 8765 4321',
                  points: '420',
                  tierLabel: '하츠코이',
                  skin: AssenMembershipSkin.sky,
                  avatar: AssenAvatar(name: '유키', hue: AssenBadgeHue.sky),
                ),
              ],
            ),
          ),
          const _Section(
            title: 'StampCard (8칸 — 채움/빈칸/리워드)',
            child: AssenStampCard(
              title: '방문 스탬프',
              filled: 5,
              rewardLabel: '체키',
            ),
          ),
          _Section(
            title: 'QRDisplay (활성 — 갱신 타이머)',
            child: AssenQrDisplay(
              memberNumber: '0000 1234 5678',
              remainingLabel: '29초',
              progress: 0.72,
              onRefresh: () {},
            ),
          ),
          _Section(
            title: 'QRDisplay (만료)',
            child: AssenQrDisplay(
              memberNumber: '0000 1234 5678',
              status: AssenQrStatus.expired,
              onRefresh: () {},
            ),
          ),
          _Section(
            title: 'ScheduleCalendar (주간 출근표)',
            child: AssenScheduleCalendar(
              days: _week,
              selectedIndex: _scheduleDay,
              todayIndex: 3,
              onSelect: (i) => setState(() => _scheduleDay = i),
            ),
          ),
          _Section(
            title: 'ReservationCard (다가옴 · 방문완료 · 취소)',
            child: Column(
              children: [
                AssenReservationCard(
                  venue: '하츠코이 본점',
                  dateTime: '6월 14일 (토) 14:00',
                  partySize: '2명',
                  status: AssenReservationStatus.upcoming,
                  ddayLabel: 'D-2',
                  primaryLabel: '예약 변경',
                  onPrimary: () {},
                  secondaryLabel: '취소',
                  onSecondary: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                const AssenReservationCard(
                  venue: '하츠코이 본점',
                  dateTime: '5월 28일 (수) 19:00',
                  partySize: '1명',
                  status: AssenReservationStatus.visited,
                ),
                const SizedBox(height: SpacingTokens.s3),
                const AssenReservationCard(
                  venue: '하츠코이 2호점',
                  dateTime: '5월 20일 (화) 13:00',
                  partySize: '3명',
                  status: AssenReservationStatus.cancelled,
                ),
              ],
            ),
          ),
          _Section(
            title: 'EventCard (예정 · 종료)',
            child: Column(
              children: [
                AssenEventCard(
                  title: '6월 콜라보 이벤트',
                  period: '6.10 – 6.30',
                  status: AssenEventStatus.upcoming,
                  ddayLabel: 'D-5',
                  slot: ColoredBox(color: colors.lavenderBg),
                  casts: const [
                    AssenScheduleCastRef(
                      name: '미오',
                      hue: AssenBadgeHue.strawberry,
                    ),
                    AssenScheduleCastRef(name: '유키', hue: AssenBadgeHue.sky),
                    AssenScheduleCastRef(name: '모카', hue: AssenBadgeHue.peach),
                  ],
                  ctaLabel: '예약하기',
                  onCta: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                AssenEventCard(
                  title: '봄 한정 디저트',
                  period: '4.1 – 4.30',
                  status: AssenEventStatus.ended,
                  slot: ColoredBox(color: colors.peachBg),
                ),
              ],
            ),
          ),
          _Section(
            title: 'CastProfileCard (기본 · 최애♥ · 출근중)',
            child: Column(
              children: [
                AssenCastProfileCard(
                  name: '모카',
                  hue: AssenBadgeHue.peach,
                  tagline: '달콤한 디저트 담당',
                  isOnShift: true,
                  isFavorite: _favorite,
                  onFavoriteChanged: (v) => setState(() => _favorite = v),
                  onTap: () {},
                ),
                const SizedBox(height: SpacingTokens.s3),
                AssenCastProfileCard(
                  name: '베리',
                  hue: AssenBadgeHue.lavender,
                  tagline: '게임 마스터',
                  isFavorite: false,
                  onFavoriteChanged: (_) {},
                  onTap: () {},
                ),
              ],
            ),
          ),
          _Section(
            title: 'SafetyReportEntry (상시 노출)',
            child: AssenSafetyReportEntry(onTap: () {}),
          ),
          _Section(
            title: 'SafetyReportTypeList (유형 9종)',
            child: AssenSafetyReportTypeList(
              selected: _reportType,
              onSelect: (t) => setState(() => _reportType = t),
            ),
          ),
          const _Section(
            title: 'EmptyState (일러스트 슬롯 + CTA)',
            child: _BoxedEmptyState(),
          ),
          _Section(
            title: 'ErrorState (재시도)',
            child: SizedBox(
              height: 320,
              child: AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () {},
              ),
            ),
          ),
          _Section(
            title: 'BottomCTA (단일 · 2분할)',
            child: Column(
              children: [
                AssenBottomCta(primaryLabel: '예약하기', onPrimary: () {}),
                const SizedBox(height: SpacingTokens.s3),
                AssenBottomCta.split(
                  primaryLabel: '다음',
                  onPrimary: () {},
                  secondaryLabel: '이전',
                  onSecondary: () {},
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// EmptyState boxed to a fixed height for the scrolling catalogue.
class _BoxedEmptyState extends StatelessWidget {
  const _BoxedEmptyState();

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return SizedBox(
      height: 360,
      child: AssenEmptyState(
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
        onAction: () {},
      ),
    );
  }
}

/// A labelled block grouping one organism's variants in the catalogue.
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
