import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/settings/payment_method.dart';
import 'package:assen_mobile/src/settings/payment_methods_controller.dart';
import 'package:assen_mobile/src/settings/settings_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 결제 수단 (payment methods) screen: the fan's saved cards, display-only.
///
/// Wired to `GET /api/fan/payment-methods` through
/// [paymentMethodsControllerProvider]. Only brand + last4 + the primary flag
/// are ever shown — never a full card number (R3/PCI). Registering a method is
/// a 대표·법무·PG gate, so a "준비 중" notice stands in for an add flow. A 401 renders
/// the shared "로그인이 필요해요" prompt; other failures fall back to [AssenErrorState]
/// with retry.
class PaymentMethodsScreen extends ConsumerWidget {
  /// Creates the payment-methods screen.
  const PaymentMethodsScreen({super.key});

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.settings);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final methods = ref.watch(paymentMethodsControllerProvider);
    return Scaffold(
      appBar: AssenAppBar(title: '결제 수단', onBack: () => _back(context)),
      body: AssenAsyncView<List<PaymentMethod>>(
        value: methods,
        loading: const _MethodsSkeleton(),
        onRetry: () =>
            ref.read(paymentMethodsControllerProvider.notifier).refresh(),
        errorBuilder: (error, _) => error is SettingsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '결제 수단을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : null,
        isEmpty: (items) => items.isEmpty,
        empty: () => ListView(
          padding: const EdgeInsets.all(SpacingTokens.s4),
          children: const [
            AssenEmptyState(
              title: '저장된 결제 수단이 없어요',
              message: '결제 수단 추가는 곧 앱에서 이용하실 수 있어요.',
            ),
            SizedBox(height: SpacingTokens.s4),
            AssenNoticeBar(message: '결제 수단 추가·변경은 준비 중이에요.'),
          ],
        ),
        data: (items) => RefreshIndicator(
          onRefresh: () =>
              ref.read(paymentMethodsControllerProvider.notifier).refresh(),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(SpacingTokens.s4),
            children: [
              for (final method in items) ...[
                _MethodCard(method: method),
                const SizedBox(height: SpacingTokens.s3),
              ],
              const SizedBox(height: SpacingTokens.s2),
              const AssenNoticeBar(message: '결제 수단 추가·변경은 준비 중이에요.'),
            ],
          ),
        ),
      ),
    );
  }
}

/// One saved method: masked label + a primary badge.
class _MethodCard extends StatelessWidget {
  const _MethodCard({required this.method});

  final PaymentMethod method;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return AssenCard(
      child: Row(
        children: [
          Icon(Icons.credit_card, color: colors.ink500),
          const SizedBox(width: SpacingTokens.s3),
          Expanded(
            child: Text(
              method.maskedLabel,
              style: TextStyle(
                fontSize: TypographyTokens.titleMSize,
                fontWeight: FontWeight.w600,
                color: colors.ink900,
              ),
            ),
          ),
          if (method.isPrimary)
            const AssenBadge(label: '기본', hue: AssenBadgeHue.sky),
        ],
      ),
    );
  }
}

/// The loading state: skeleton method rows.
class _MethodsSkeleton extends StatelessWidget {
  const _MethodsSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 3,
      separatorBuilder: (context, index) =>
          const SizedBox(height: SpacingTokens.s3),
      itemBuilder: (context, index) => const AssenCard(
        child: Row(
          children: [
            AssenSkeleton(width: 32, height: 24),
            SizedBox(width: SpacingTokens.s3),
            Expanded(child: AssenSkeleton(width: 160)),
          ],
        ),
      ),
    );
  }
}
