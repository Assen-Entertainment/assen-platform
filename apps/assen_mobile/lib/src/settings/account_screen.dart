import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/account_repository.dart';
import 'package:assen_mobile/src/settings/settings_controller.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 계정 관리 (account) screen: account info + 회원 탈퇴 (withdrawal).
///
/// Reuses [settingsControllerProvider] (`GET /api/fan/me`) for the identity and
/// [AccountRepository.withdraw] (`POST /api/fan/account/withdraw`) for the
/// irreversible 탈퇴. Withdrawal anonymises the account in place and revokes all
/// sessions (D3, 2026-07-12); it is gated behind a destructive confirm dialog,
/// signs the app out on success and routes to login. A 401 renders the shared
/// "로그인이 필요해요" prompt; other failures fall back to [AssenErrorState].
class AccountScreen extends ConsumerWidget {
  /// Creates the account screen.
  const AccountScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.settings);
  }

  Future<void> _confirmWithdraw(BuildContext context, WidgetRef ref) async {
    final confirmed = await AssenDialog.show<bool>(
      context,
      dialog: AssenDialog(
        title: '정말 탈퇴하시겠어요?',
        message: '탈퇴하면 계정 정보가 익명 처리되고 모든 로그인 세션이 해제돼요. 이 작업은 되돌릴 수 없어요.',
        confirmLabel: '탈퇴하기',
        destructive: true,
        cancelLabel: '취소',
        onCancel: () => Navigator.of(context).pop(false),
        onConfirm: () => Navigator.of(context).pop(true),
      ),
    );
    if (confirmed != true || !context.mounted) return;
    await _withdraw(context, ref);
  }

  Future<void> _withdraw(BuildContext context, WidgetRef ref) async {
    try {
      await ref.read(accountRepositoryProvider).withdraw();
      ref.read(authControllerProvider.notifier).signOut();
      if (context.mounted) context.go(RoutePaths.login);
    } on SettingsAuthRequiredException {
      // Already signed out server-side: land on the login wall regardless.
      ref.read(authControllerProvider.notifier).signOut();
      if (context.mounted) context.go(RoutePaths.login);
    } on Object {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('탈퇴 처리에 실패했어요. 잠시 후 다시 시도해 주세요.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(settingsControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '계정 관리', onBack: () => _back(context)),
      body: AssenAsyncView<FanMe>(
        value: me,
        loading: const _AccountSkeleton(),
        onRetry: () => ref.read(settingsControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => error is SettingsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '계정 정보를 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : null,
        data: (fan) => _AccountBody(
          fan: fan,
          onWithdraw: () => _confirmWithdraw(context, ref),
        ),
      ),
    );
  }
}

/// The loaded account view: identity rows over the 회원 탈퇴 action.
class _AccountBody extends StatelessWidget {
  const _AccountBody({required this.fan, required this.onWithdraw});

  final FanMe fan;
  final VoidCallback onWithdraw;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: [
        const AssenSectionHeader(title: '계정 정보'),
        AssenListItem(
          title: '닉네임',
          showChevron: false,
          trailing: Text(
            fan.nickname,
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink600,
            ),
          ),
        ),
        AssenListItem(
          title: '역할',
          showChevron: false,
          trailing: Text(
            fan.role == 'creator' ? '크리에이터' : '팬',
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink600,
            ),
          ),
        ),
        if (fan.handle != null)
          AssenListItem(
            title: '핸들',
            showChevron: false,
            trailing: Text(
              '@${fan.handle}',
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                color: colors.ink600,
              ),
            ),
          ),
        const SizedBox(height: SpacingTokens.s8),
        const AssenSectionHeader(title: '회원 탈퇴'),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
          child: Text(
            '탈퇴하면 계정 정보가 익명 처리되고 다시 복구할 수 없어요. '
            '법령에 따라 보관이 필요한 거래·분쟁 기록은 익명화된 상태로 유지돼요.',
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              height: 1.5,
              color: colors.ink500,
            ),
          ),
        ),
        const SizedBox(height: SpacingTokens.s3),
        AssenButton(
          label: '회원 탈퇴',
          style: AssenButtonStyle.secondary,
          expand: true,
          onPressed: onWithdraw,
        ),
      ],
    );
  }
}

/// The loading state: skeleton account rows.
class _AccountSkeleton extends StatelessWidget {
  const _AccountSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenSkeleton(width: 120),
          SizedBox(height: SpacingTokens.s4),
          AssenSkeleton(width: double.infinity, height: 48),
          SizedBox(height: SpacingTokens.s3),
          AssenSkeleton(width: double.infinity, height: 48),
        ],
      ),
    );
  }
}
