import 'package:assen_mobile/src/app/router.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// One intro slide: an icon over a headline and a supporting line.
@immutable
class _OnboardingPage {
  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

const List<_OnboardingPage> _pages = [
  _OnboardingPage(
    icon: Icons.favorite_border,
    title: 'Assen에 오신 걸 환영해요',
    body: '좋아하는 크리에이터를 발견하고 응원해 보세요.',
  ),
  _OnboardingPage(
    icon: Icons.dynamic_feed_outlined,
    title: '피드로 소식을 받아보세요',
    body: '크리에이터의 새 게시물과 알림을 놓치지 마세요.',
  ),
  _OnboardingPage(
    icon: Icons.storefront_outlined,
    title: '스토어에서 만나요',
    body: '굿즈·디지털·티켓까지 한곳에서 둘러볼 수 있어요.',
  ),
  _OnboardingPage(
    icon: Icons.explore_outlined,
    title: '시작할 준비가 됐어요',
    body: '먼저 둘러보고, 마음에 드는 크리에이터를 팔로우하세요.',
  ),
];

/// The 온보딩 (onboarding) screen: a static intro to the app.
///
/// Intro/value slides only — a [PageView] of app highlights ending in a
/// "둘러보기 시작" CTA that opens discovery ([RoutePaths.discovery]). Reached from
/// 설정 → "앱 소개 다시 보기"; it is intentionally NOT auto-shown on first launch
/// (that needs local persistence, out of scope). The last slide carries a card
/// linking to [RoutePaths.login], where consent (약관 동의) is captured on signup
/// and 19+ 본인인증 runs from 설정 — this screen itself calls NO consent/verify
/// endpoint and stores NO agreement.
class OnboardingScreen extends StatefulWidget {
  /// Creates the onboarding screen.
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  bool get _isLast => _index == _pages.length - 1;

  void _next() {
    if (_isLast) {
      _finish();
      return;
    }
    _controller.nextPage(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
    );
  }

  /// Leaves onboarding: pop back to the entry point (설정, when pushed) if there
  /// is one, otherwise go to discovery (a direct/deep-link entry).
  void _finish() {
    context.canPop() ? context.pop() : context.go(RoutePaths.discovery);
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.s2,
                  vertical: SpacingTokens.s1,
                ),
                child: AssenButton(
                  label: '건너뛰기',
                  style: AssenButtonStyle.ghost,
                  onPressed: _finish,
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                onPageChanged: (index) => setState(() => _index = index),
                itemCount: _pages.length,
                itemBuilder: (context, index) => _OnboardingSlide(
                  page: _pages[index],
                  showConsentNotice: index == _pages.length - 1,
                ),
              ),
            ),
            _Dots(count: _pages.length, active: _index, colors: colors),
            const SizedBox(height: SpacingTokens.s4),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                SpacingTokens.s4,
                0,
                SpacingTokens.s4,
                SpacingTokens.s4,
              ),
              child: AssenButton(
                label: _isLast ? '둘러보기 시작' : '다음',
                expand: true,
                onPressed: _next,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// One rendered slide: the centred icon/title/body, plus the disabled
/// consent-notice card on the final slide.
class _OnboardingSlide extends StatelessWidget {
  const _OnboardingSlide({required this.page, required this.showConsentNotice});

  final _OnboardingPage page;
  final bool showConsentNotice;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.s6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(height: SpacingTokens.s8),
          Container(
            width: SpacingTokens.s16,
            height: SpacingTokens.s16,
            decoration: BoxDecoration(
              color: colors.indigo100,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              page.icon,
              size: SpacingTokens.s8,
              color: colors.indigoInk,
            ),
          ),
          const SizedBox(height: SpacingTokens.s6),
          Text(
            page.title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: TypographyTokens.headlineSize,
              fontWeight: FontWeight.w800,
              color: colors.ink900,
            ),
          ),
          const SizedBox(height: SpacingTokens.s3),
          Text(
            page.body,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: TypographyTokens.bodyLSize,
              height: 1.5,
              color: colors.ink600,
            ),
          ),
          if (showConsentNotice) ...[
            const SizedBox(height: SpacingTokens.s8),
            const _ConsentNoticeCard(),
          ],
        ],
      ),
    );
  }
}

/// The final-slide card: a live CTA into the sign-in flow.
///
/// Consent (약관 동의) is captured on the signup step of [RoutePaths.login] and
/// 19+ 본인인증 runs from 설정 after sign-in, so this card no longer holds an inert
/// gate — it routes to login. It issues NO consent/verify request itself and
/// stores NO agreement; the login/settings flows own those (mock, PII-free).
class _ConsentNoticeCard extends StatelessWidget {
  const _ConsentNoticeCard();

  @override
  Widget build(BuildContext context) {
    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AssenNoticeBar(
            message: '로그인 후 약관 동의와 본인인증(19+)을 진행할 수 있어요.',
          ),
          const SizedBox(height: SpacingTokens.s4),
          AssenButton(
            label: '로그인하고 시작하기',
            expand: true,
            onPressed: () => context.go(RoutePaths.login),
          ),
        ],
      ),
    );
  }
}

/// The page-position dots under the [PageView].
class _Dots extends StatelessWidget {
  const _Dots({
    required this.count,
    required this.active,
    required this.colors,
  });

  final int count;
  final int active;
  final AssenColors colors;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var i = 0; i < count; i++)
          Container(
            width: SpacingTokens.s2,
            height: SpacingTokens.s2,
            margin: const EdgeInsets.symmetric(horizontal: SpacingTokens.s1),
            decoration: BoxDecoration(
              color: i == active ? colors.indigo500 : colors.neutral200,
              shape: BoxShape.circle,
            ),
          ),
      ],
    );
  }
}
