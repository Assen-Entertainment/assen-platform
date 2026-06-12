import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/router/routes.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// One onboarding slide's copy + pastel motif hue.
class _Slide {
  const _Slide({
    required this.title,
    required this.body,
    required this.hue,
    required this.icon,
  });

  final String title;
  final String body;
  final AssenBadgeHue hue;
  final IconData icon;
}

/// The mobile first-run onboarding (plan §4.3 — landing mood, re-built in the
/// design system; no GSAP parity).
///
/// Reconstructs the landing's light-retro-cute mood (cream + pastel, cheki
/// motif) as a static [PageView] of 2–3 slides over the cream surface, with a
/// bottom CTA to 로그인/가입. Only the framework's default page transition is
/// used (no complex motion). Colours come from [AssenColors]; copy is generic
/// (no fabricated scenes — landing copy constraints).
class OnboardingScreen extends StatefulWidget {
  /// Creates the onboarding screen.
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _page = 0;

  static const List<_Slide> _slides = [
    _Slide(
      title: '하츠코이를 손안에',
      body: '디지털 회원증으로 입장하고\n방문마다 스탬프를 모아요.',
      hue: AssenBadgeHue.strawberry,
      icon: Icons.badge_outlined,
    ),
    _Slide(
      title: '오늘의 출근을 한눈에',
      body: '최애 캐스트의 출근표를 확인하고\n방문 전에 일정을 챙겨요.',
      hue: AssenBadgeHue.sky,
      icon: Icons.calendar_month_outlined,
    ),
    _Slide(
      title: '체키로 남기는 추억',
      body: '받은 체키를 앨범에 모으고\n수집 도감을 채워가요.',
      hue: AssenBadgeHue.lavender,
      icon: Icons.photo_library_outlined,
    ),
  ];

  bool get _isLast => _page == _slides.length - 1;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _next() {
    if (_isLast) {
      context.go(FanRoutes.login);
      return;
    }
    _controller.nextPage(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return Scaffold(
      backgroundColor: colors.cream50,
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.all(SpacingTokens.s3),
                child: AssenButton(
                  label: '건너뛰기',
                  style: AssenButtonStyle.ghost,
                  onPressed: () => context.go(FanRoutes.login),
                ),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                onPageChanged: (i) => setState(() => _page = i),
                itemCount: _slides.length,
                itemBuilder: (context, i) =>
                    _OnboardingSlide(slide: _slides[i]),
              ),
            ),
            _Dots(count: _slides.length, active: _page),
            const SizedBox(height: SpacingTokens.s5),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                SpacingTokens.screenMargin,
                0,
                SpacingTokens.screenMargin,
                SpacingTokens.s4,
              ),
              child: Column(
                children: [
                  AssenButton(
                    label: _isLast ? '시작하기' : '다음',
                    expand: true,
                    onPressed: _next,
                  ),
                  const SizedBox(height: SpacingTokens.s2),
                  AssenButton(
                    label: '이미 계정이 있어요',
                    style: AssenButtonStyle.ghost,
                    expand: true,
                    onPressed: () => context.go(FanRoutes.login),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// A single onboarding slide: a pastel cheki-framed motif over copy.
class _OnboardingSlide extends StatelessWidget {
  const _OnboardingSlide({required this.slide});

  final _Slide slide;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final bg = _hueBg(colors, slide.hue);
    final ink = _hueInk(colors, slide.hue);

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.screenMargin,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // A cheki-frame-styled tile (white border, pastel window) — the
          // landing's instax motif, static.
          Container(
            width: SpacingTokens.s16,
            height: SpacingTokens.s16,
            padding: const EdgeInsets.all(SpacingTokens.s2),
            decoration: BoxDecoration(
              color: colors.white,
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.md),
              ),
              border: Border.all(color: colors.ink100),
            ),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: bg,
                borderRadius: const BorderRadius.all(
                  Radius.circular(RadiusTokens.sm),
                ),
              ),
              child: Icon(slide.icon, size: SpacingTokens.s12, color: ink),
            ),
          ),
          const SizedBox(height: SpacingTokens.s8),
          Text(
            slide.title,
            textAlign: TextAlign.center,
            style: TypographyTokens.displayS.copyWith(
              fontWeight: FontWeight.w800,
              color: colors.ink900,
            ),
          ),
          const SizedBox(height: SpacingTokens.s3),
          Text(
            slide.body,
            textAlign: TextAlign.center,
            style: TypographyTokens.bodyL.copyWith(
              height: 1.5,
              color: colors.ink700,
            ),
          ),
        ],
      ),
    );
  }

  Color _hueBg(AssenColors c, AssenBadgeHue hue) => switch (hue) {
    AssenBadgeHue.strawberry => c.strawberryBg,
    AssenBadgeHue.peach => c.peachBg,
    AssenBadgeHue.lemon => c.lemonBg,
    AssenBadgeHue.matcha => c.matchaBg,
    AssenBadgeHue.sky => c.skyBg,
    AssenBadgeHue.lavender => c.lavenderBg,
  };

  Color _hueInk(AssenColors c, AssenBadgeHue hue) => switch (hue) {
    AssenBadgeHue.strawberry => c.strawberryInk,
    AssenBadgeHue.peach => c.peachInk,
    AssenBadgeHue.lemon => c.lemonInk,
    AssenBadgeHue.matcha => c.matchaInk,
    AssenBadgeHue.sky => c.skyInk,
    AssenBadgeHue.lavender => c.lavenderInk,
  };
}

/// The page-position dots under the carousel.
class _Dots extends StatelessWidget {
  const _Dots({required this.count, required this.active});

  final int count;
  final int active;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        for (var i = 0; i < count; i++) ...[
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: i == active ? SpacingTokens.s5 : SpacingTokens.s2,
            height: SpacingTokens.s2,
            decoration: BoxDecoration(
              color: i == active ? colors.roseMain : colors.ink200,
              borderRadius: const BorderRadius.all(
                Radius.circular(RadiusTokens.full),
              ),
            ),
          ),
          if (i != count - 1) const SizedBox(width: SpacingTokens.s2),
        ],
      ],
    );
  }
}
