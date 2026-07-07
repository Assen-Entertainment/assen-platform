import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/auth/auth_controller.dart';
import 'package:assen_mobile/src/mypage/fan_me.dart';
import 'package:assen_mobile/src/settings/settings_controller.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 설정 (settings) screen: the signed-in fan's profile and account actions.
///
/// Wired to `GET /api/fan/me` through [settingsControllerProvider]. It shows the
/// identity (avatar + nickname + role/handle), lets the fan edit their nickname
/// (`PATCH /api/fan/me`, reflected on success), links to the app intro
/// ([RoutePaths.onboarding]) and signs out ([AuthController.signOut]). The
/// derived 성인/KYC 인증 flags are shown as read-only badges only — real 본인인증 is a
/// 법무 gate and is deliberately not executed here (a "준비 중" notice explains).
/// A 401 renders the "로그인이 필요해요" prompt; other failures fall back to
/// [AssenErrorState] with retry.
class SettingsScreen extends ConsumerWidget {
  /// Creates the settings screen.
  const SettingsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.mypage);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(settingsControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '설정', onBack: () => _back(context)),
      body: me.when(
        loading: () => const _SettingsSkeleton(),
        error: (error, stackTrace) => error is SettingsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '설정을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () =>
                    ref.read(settingsControllerProvider.notifier).refresh(),
              ),
        data: (fan) => _SettingsBody(fan: fan),
      ),
    );
  }
}

/// The loaded settings view: identity, account rows, 인증 state and sign-out.
class _SettingsBody extends ConsumerWidget {
  const _SettingsBody({required this.fan});

  final FanMe fan;

  Future<void> _editNickname(BuildContext context) async {
    await AssenBottomSheet.show<void>(
      context,
      sheet: AssenBottomSheet(
        title: '닉네임 변경',
        child: _NicknameEditor(currentNickname: fan.nickname),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final subtitle = fan.handle == null
        ? _roleLabel(fan.role)
        : '@${fan.handle}';

    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: [
        Row(
          children: [
            AssenAvatar(
              name: fan.nickname,
              size: AssenAvatarSize.l,
              imageProvider: fan.avatarUrl == null
                  ? null
                  : NetworkImage(fan.avatarUrl!),
            ),
            const SizedBox(width: SpacingTokens.s4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    fan.nickname,
                    style: TextStyle(
                      fontSize: TypographyTokens.titleLSize,
                      fontWeight: FontWeight.w800,
                      color: colors.ink900,
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.s1),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: TypographyTokens.bodyMSize,
                      color: colors.ink500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.s6),

        const AssenSectionHeader(title: '계정'),
        AssenListItem(
          title: '닉네임',
          subtitle: fan.nickname,
          onTap: () => _editNickname(context),
        ),
        AssenListItem(
          title: '역할',
          trailing: Text(
            _roleLabel(fan.role),
            style: TextStyle(
              fontSize: TypographyTokens.bodyMSize,
              color: colors.ink700,
            ),
          ),
        ),
        if (fan.handle != null)
          AssenListItem(
            title: '핸들',
            trailing: Text(
              '@${fan.handle}',
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                color: colors.ink700,
              ),
            ),
          ),

        const SizedBox(height: SpacingTokens.s4),
        const AssenSectionHeader(title: '인증'),
        AssenListItem(
          title: '성인 인증 (19+)',
          showChevron: false,
          trailing: fan.adultVerified
              ? const AssenStatusBadge(
                  kind: AssenStatusKind.confirmed,
                  label: '인증 완료',
                )
              : const AssenStatusBadge(
                  kind: AssenStatusKind.pending,
                  label: '미인증',
                ),
        ),
        AssenListItem(
          title: '본인 인증',
          showChevron: false,
          trailing: AssenStatusBadge(
            kind: _kycKind(fan.kycStatus),
            label: _kycLabel(fan.kycStatus),
          ),
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: SpacingTokens.s2),
          child: AssenNoticeBar(
            message: '본인인증은 준비 중이에요. 곧 앱에서 이용하실 수 있습니다.',
          ),
        ),

        const SizedBox(height: SpacingTokens.s4),
        const AssenSectionHeader(title: '앱'),
        AssenListItem(
          title: '앱 소개 다시 보기',
          onTap: () => context.go(RoutePaths.onboarding),
        ),

        const SizedBox(height: SpacingTokens.s8),
        AssenButton(
          label: '로그아웃',
          style: AssenButtonStyle.secondary,
          expand: true,
          onPressed: () {
            ref.read(authControllerProvider.notifier).signOut();
            context.go(RoutePaths.discovery);
          },
        ),
      ],
    );
  }
}

/// The nickname edit sheet body: a validated 1–40 char field + a save action.
///
/// A [ConsumerStatefulWidget] so it owns the input controller and the in-flight
/// state. Saving calls [SettingsController.updateNickname] (`PATCH /api/fan/me`);
/// on success the sheet closes and the loaded profile refreshes, on failure the
/// error surfaces inline without closing.
class _NicknameEditor extends ConsumerStatefulWidget {
  const _NicknameEditor({required this.currentNickname});

  final String currentNickname;

  @override
  ConsumerState<_NicknameEditor> createState() => _NicknameEditorState();
}

class _NicknameEditorState extends ConsumerState<_NicknameEditor> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.currentNickname,
  );
  String? _errorText;
  bool _saving = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final nickname = _controller.text.trim();
    if (nickname.isEmpty || nickname.length > 40) {
      setState(() => _errorText = '닉네임은 1~40자로 입력해 주세요.');
      return;
    }
    setState(() {
      _saving = true;
      _errorText = null;
    });
    try {
      await ref
          .read(settingsControllerProvider.notifier)
          .updateNickname(nickname);
      if (!mounted) return;
      Navigator.of(context).pop();
    } on Exception {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _errorText = '닉네임을 변경하지 못했어요. 다시 시도해 주세요.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.s6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AssenTextField(
            label: '닉네임',
            controller: _controller,
            hintText: '새 닉네임',
            errorText: _errorText,
            helperText: '1~40자',
          ),
          const SizedBox(height: SpacingTokens.s4),
          AssenButton(
            label: '저장',
            expand: true,
            onPressed: _saving ? null : _save,
          ),
        ],
      ),
    );
  }
}

/// The Korean label for the account [role] (`fan`/`creator`).
String _roleLabel(String role) => switch (role) {
  'fan' => '팬',
  'creator' => '크리에이터',
  _ => role,
};

/// The Korean label for a KYC [status] (server `kyc_status`).
String _kycLabel(String status) => switch (status) {
  'verified' => '인증 완료',
  'pending' => '심사중',
  'failed' => '인증 실패',
  _ => '미인증',
};

/// Maps a KYC [status] to the semantic badge hue (verified→success,
/// pending→in-progress, failed→cancelled, unverified→neutral).
AssenStatusKind _kycKind(String status) => switch (status) {
  'verified' => AssenStatusKind.confirmed,
  'pending' => AssenStatusKind.done,
  'failed' => AssenStatusKind.cancelled,
  _ => AssenStatusKind.pending,
};

/// The loading state: an identity-header skeleton over a couple of rows.
class _SettingsSkeleton extends StatelessWidget {
  const _SettingsSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AssenSkeleton(width: 72, height: 72, radius: 36),
              SizedBox(width: SpacingTokens.s4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AssenSkeleton(width: 140),
                    SizedBox(height: SpacingTokens.s2),
                    AssenSkeleton(width: 100),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: SpacingTokens.s8),
          AssenSkeleton(width: 120),
          SizedBox(height: SpacingTokens.s4),
          AssenSkeleton(width: double.infinity, height: 44),
          SizedBox(height: SpacingTokens.s3),
          AssenSkeleton(width: double.infinity, height: 44),
        ],
      ),
    );
  }
}
