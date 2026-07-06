import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:ui_kit/src/atoms/avatar.dart';
import 'package:ui_kit/src/atoms/badges.dart';
import 'package:ui_kit/src/atoms/icon_button.dart';
import 'package:ui_kit/src/organisms/app_bar.dart';
import 'package:ui_kit/src/organisms/bottom_cta.dart';
import 'package:ui_kit/src/organisms/cover_header.dart';
import 'package:ui_kit/src/organisms/empty_state.dart';
import 'package:ui_kit/src/organisms/error_state.dart';
import 'package:ui_kit/src/organisms/membership_card.dart';
import 'package:ui_kit/src/organisms/product_card.dart';

/// A single-screen gallery of every Organism for visual review.
///
/// The human-facing review surface for the ASS-88 Organisms layer: it renders
/// the domain-agnostic organisms (MembershipCard, EmptyState, ErrorState,
/// BottomCTA — each in its relevant variants/states) on the cream surface so
/// reviewers and the `flutter build web` smoke test exercise the layer at
/// once — the same review pattern as `AtomCatalog`/`MoleculeCatalog`. It is
/// stateful so the interactive TabBar responds live; AppBar and TabBar frame
/// the screen so the navigation organisms run in their real chrome roles.
class OrganismCatalog extends StatefulWidget {
  /// Creates the organism catalogue screen.
  const OrganismCatalog({super.key});

  @override
  State<OrganismCatalog> createState() => _OrganismCatalogState();
}

class _OrganismCatalogState extends State<OrganismCatalog> {
  int _tab = 0;

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
          _Section(
            title: 'CoverHeader (프로필 커버 + 아바타)',
            child: AssenCoverHeader(
              title: '미오',
              subtitle: '@mio · 버추얼',
              accent: colors.lavenderBg,
              avatar: const AssenAvatar(
                name: '미오',
                size: AssenAvatarSize.l,
                hue: AssenBadgeHue.lavender,
              ),
              badge: Icon(Icons.verified, color: colors.skyInk, size: 20),
            ),
          ),
          _Section(
            title: 'ProductCard (수익 아이템)',
            child: AssenProductCard(
              title: '한정 아크릴 스탠드',
              priceLabel: '₩18,000',
              tagLabel: '굿즈',
              meta: '선착순 100개',
              onTap: () {},
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
