import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/settings/marketing_consent.dart';
import 'package:assen_mobile/src/settings/marketing_controller.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 알림 설정 (marketing consent) screen: per-channel opt-in toggles.
///
/// Wired to `GET/PUT /api/fan/marketing` through [marketingControllerProvider].
/// Consent is optional (D8) — any combination, including all-off, is valid and
/// never blocks service use; the copy says so. Push/SMS are live toggles; email
/// is shown disabled (not collected yet). Each flip saves immediately and
/// optimistically, reverting with a toast on failure. A 401 renders the shared
/// "로그인이 필요해요" prompt; other failures fall back to [AssenErrorState].
class NotificationSettingsScreen extends ConsumerWidget {
  /// Creates the notification-settings screen.
  const NotificationSettingsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.settings);
  }

  Future<void> _toggle(
    BuildContext context,
    WidgetRef ref,
    MarketingChannel channel, {
    required bool enabled,
  }) async {
    try {
      await ref
          .read(marketingControllerProvider.notifier)
          .setChannel(channel, enabled: enabled);
    } on SettingsAuthRequiredException {
      if (context.mounted) context.go(RoutePaths.login);
    } on Object {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('설정을 저장하지 못했어요. 다시 시도해 주세요.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final consent = ref.watch(marketingControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '알림 설정', onBack: () => _back(context)),
      body: AssenAsyncView<MarketingConsent>(
        value: consent,
        loading: const _ConsentSkeleton(),
        onRetry: () => ref.read(marketingControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => error is SettingsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '알림 설정을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : null,
        data: (value) => _ConsentBody(consent: value, onToggle: _toggle),
      ),
    );
  }
}

/// The loaded toggles: 마케팅 수신 동의 per channel over an optional-consent note.
class _ConsentBody extends ConsumerWidget {
  const _ConsentBody({required this.consent, required this.onToggle});

  final MarketingConsent consent;
  final Future<void> Function(
    BuildContext,
    WidgetRef,
    MarketingChannel, {
    required bool enabled,
  })
  onToggle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: [
        const AssenNoticeBar(
          message: '마케팅 정보 수신은 선택 사항이에요. 동의하지 않아도 서비스 이용에는 영향이 없어요.',
        ),
        const SizedBox(height: SpacingTokens.s4),
        const AssenSectionHeader(title: '마케팅 수신 동의'),
        AssenListItem(
          title: '앱 푸시 알림',
          subtitle: '이벤트·소식을 푸시로 받아요.',
          trailing: AssenSwitch(
            value: consent.push,
            onChanged: (v) =>
                onToggle(context, ref, MarketingChannel.push, enabled: v),
          ),
        ),
        AssenListItem(
          title: '문자(SMS)',
          subtitle: '이벤트·소식을 문자로 받아요.',
          trailing: AssenSwitch(
            value: consent.sms,
            onChanged: (v) =>
                onToggle(context, ref, MarketingChannel.sms, enabled: v),
          ),
        ),
        AssenListItem(
          title: '이메일',
          subtitle: '이메일 수신은 아직 준비 중이에요.',
          trailing: AssenSwitch(value: consent.email, onChanged: null),
        ),
        const SizedBox(height: SpacingTokens.s4),
        Text(
          '동의 이력은 안전하게 기록되며, 언제든지 이 화면에서 변경할 수 있어요.',
          style: TextStyle(
            fontSize: TypographyTokens.bodySSize,
            color: colors.ink500,
          ),
        ),
      ],
    );
  }
}

/// The loading state: skeleton toggle rows.
class _ConsentSkeleton extends StatelessWidget {
  const _ConsentSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenSkeleton(width: double.infinity, height: 56),
          SizedBox(height: SpacingTokens.s4),
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
