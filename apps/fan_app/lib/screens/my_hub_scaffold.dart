import 'package:core_tokens/core_tokens.dart';
import 'package:fan_app/mock/fan_mock_data.dart';
import 'package:fan_app/router/routes.dart';
import 'package:features/features.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// Which `/my` sub-page the [MyHubScaffold] is rendering (ASS-147 Slice 4).
///
/// The value is the URL-derived selection: each `/my/*` screen passes its own
/// page here, so the active menu highlight and the detail pane come from the
/// current route — no provider, deep-linkable, and reset on return to `/my`.
enum MySubPage {
  /// The `/my` hub root (no sub-page selected).
  home,

  /// `/my/visits` — 나의 하츠코이 기록.
  visits,

  /// `/my/points` — 포인트 내역.
  points,

  /// `/my/notifications` — 알림 설정.
  notifications,
}

/// The My hub shell that turns the account sub-pages into a Material 3 inline
/// list-detail at desktop widths (ASS-147 Slice 4, §4.4a true inline).
///
/// `/my` and its children (`/my/visits`, `/my/points`, `/my/notifications`) are
/// in-branch nested routes, so the detail pane can render inline. Below the
/// large content width this returns [narrow] verbatim (the existing full-screen
/// template; tapping a menu row pushes the child route — the unchanged mobile
/// flow). At large and wider it renders a fixed menu pane beside [detail] (the
/// selected sub-page's chrome-less body). Selecting a menu row is a
/// `context.go('/my/<sub>')`, so the URL drives the selection: it is
/// deep-linkable and resets to the prompt on return to `/my` (re-tap-to-root),
/// with no app-global provider holding a stale sub-page.
class MyHubScaffold extends ConsumerWidget {
  /// Creates the My hub shell for [active], with [narrow] for compact/medium and
  /// [detail] mounted in the detail pane at large+.
  const MyHubScaffold({
    required this.active,
    required this.narrow,
    required this.detail,
    super.key,
  });

  /// The current sub-page (drives the active menu highlight + detail pane).
  final MySubPage active;

  /// The compact/medium full-screen rendering (the existing template/screen).
  final Widget narrow;

  /// The chrome-less body mounted in the detail pane at large+.
  final Widget detail;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;

    return LayoutBuilder(
      builder: (context, constraints) {
        // Gate on the width the list-detail scaffold will receive (after the
        // screen-margin padding) so the hub and the scaffold agree on the
        // breakpoint — same rule as the events surface (no dead band).
        final contentWidth =
            constraints.maxWidth - SpacingTokens.screenMargin * 2;
        final wide = AssenWindowSize.fromWidth(
          contentWidth,
        ).atLeast(AssenWindowSize.large);

        if (!wide) return narrow;

        return Scaffold(
          backgroundColor: colors.cream50,
          appBar: const AssenAppBar(title: '마이'),
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
                    AssenListDetailScaffold(
                      listPaneWidth: 300,
                      list: _MyMenu(
                        active: active,
                        onSignOut: () => _signOut(ref),
                      ),
                      detail: detail,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  void _signOut(WidgetRef ref) =>
      ref.read(authSessionProvider.notifier).signOut();
}

/// The shared My menu rendered in the list pane (profile + account rows).
class _MyMenu extends StatelessWidget {
  const _MyMenu({required this.active, required this.onSignOut});

  final MySubPage active;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    const member = FanMockData.member;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            SpacingTokens.s2,
            SpacingTokens.s2,
            SpacingTokens.s2,
            SpacingTokens.s4,
          ),
          child: Row(
            children: [
              AssenAvatar(
                name: member.name,
                hue: AssenBadgeHue.strawberry,
              ),
              const SizedBox(width: SpacingTokens.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      member.name,
                      style: TypographyTokens.titleM.copyWith(
                        fontWeight: FontWeight.w800,
                        color: colors.ink900,
                      ),
                    ),
                    const SizedBox(height: SpacingTokens.s1),
                    Text(
                      member.tierLabel,
                      style: TypographyTokens.captionMicro.copyWith(
                        color: colors.ink700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        _MenuRow(
          icon: Icons.qr_code_2,
          title: '회원증 QR',
          onTap: () => context.push(FanRoutes.qr),
        ),
        _MenuRow(
          icon: Icons.history,
          title: '나의 하츠코이 기록',
          selected: active == MySubPage.visits,
          onTap: () => context.go(FanRoutes.visitHistory),
        ),
        const _MenuRow(
          icon: Icons.confirmation_number_outlined,
          title: '쿠폰함',
        ),
        _MenuRow(
          icon: Icons.stars_outlined,
          title: '포인트 내역',
          selected: active == MySubPage.points,
          onTap: () => context.go(FanRoutes.pointsHistory),
        ),
        _MenuRow(
          icon: Icons.notifications_outlined,
          title: '알림 설정',
          selected: active == MySubPage.notifications,
          onTap: () => context.go(FanRoutes.notificationSettings),
        ),
        const _MenuRow(
          icon: Icons.flag_outlined,
          title: '신고하기',
        ),
        const SizedBox(height: SpacingTokens.s4),
        _MenuRow(
          icon: Icons.logout,
          title: '로그아웃',
          tint: colors.redInk,
          onTap: onSignOut,
        ),
      ],
    );
  }
}

/// A single My menu row. A null [onTap] renders a non-interactive placeholder
/// (muted, not keyboard-focusable, no button semantics) for surfaces that are
/// not built yet; otherwise it is a tinted, keyboard-focusable InkWell.
class _MenuRow extends StatelessWidget {
  const _MenuRow({
    required this.icon,
    required this.title,
    this.onTap,
    this.selected = false,
    this.tint,
  });

  final IconData icon;
  final String title;
  final VoidCallback? onTap;
  final bool selected;
  final Color? tint;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final disabled = onTap == null;
    final foreground = disabled
        ? colors.ink300
        : (tint ?? (selected ? colors.roseMain : colors.ink700));

    final rowContent = Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.s3,
        vertical: SpacingTokens.s3,
      ),
      child: Row(
        children: [
          Icon(icon, color: foreground, size: SpacingTokens.s6),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Text(
              title,
              style: TypographyTokens.bodyM.copyWith(
                color: foreground,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );

    // Unbuilt surfaces: a plain muted row, not announced as a button and not in
    // the focus order, so it is not a do-nothing keyboard/AT trap.
    if (disabled) {
      return Semantics(enabled: false, child: rowContent);
    }

    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        color: selected ? colors.strawberryBg : Colors.transparent,
        borderRadius: const BorderRadius.all(Radius.circular(RadiusTokens.md)),
        child: InkWell(
          onTap: onTap,
          borderRadius: const BorderRadius.all(
            Radius.circular(RadiusTokens.md),
          ),
          child: rowContent,
        ),
      ),
    );
  }
}
