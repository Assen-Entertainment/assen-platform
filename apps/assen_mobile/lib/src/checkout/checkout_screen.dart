import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/checkout/checkout_controller.dart';
import 'package:assen_mobile/src/checkout/checkout_repository.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/common/json_parse.dart';
import 'package:assen_mobile/src/common/now.dart';
import 'package:assen_mobile/src/orders/order.dart';
import 'package:assen_mobile/src/store/product.dart';
import 'package:assen_mobile/src/store/store_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 결제 (checkout) screen: a mock order for one product.
///
/// Wired to `GET /api/products/{id}` (the summary target, via
/// [checkoutProductProvider]) and `POST /api/orders` (place order, via
/// [CheckoutRepository]). No real payment is taken — the server records a
/// `paid` mock order and no money moves (대표·PG 게이트). The pay action is
/// fail-closed behind [paymentAvailableProvider]: when the rail is off it is
/// replaced by a "준비 중" notice. A physical (goods) order collects a delivery
/// address (required by the server, else rejected). On success the screen shows
/// an order confirmation; a 401 drops to the login wall.
class CheckoutScreen extends ConsumerStatefulWidget {
  /// Creates the checkout screen for [productId] (optionally [qty]/[option]).
  const CheckoutScreen({
    required this.productId,
    this.qty = 1,
    this.option = '',
    super.key,
  });

  /// The id of the product to buy.
  final String productId;

  /// The quantity to buy (defaults to 1).
  final int qty;

  /// The chosen purchase option, if any.
  final String option;

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  final _recipientName = TextEditingController();
  final _recipientPhone = TextEditingController();
  final _postalCode = TextEditingController();
  final _address1 = TextEditingController();
  final _address2 = TextEditingController();

  bool _submitting = false;
  String? _errorText;
  Order? _placed;

  /// A per-session idempotency key so a retry (blip) can't double-order.
  late final String _idempotencyKey =
      '${widget.productId}-${ref.read(nowProvider).microsecondsSinceEpoch}';

  @override
  void dispose() {
    _recipientName.dispose();
    _recipientPhone.dispose();
    _postalCode.dispose();
    _address1.dispose();
    _address2.dispose();
    super.dispose();
  }

  void _back(BuildContext context) {
    context.canPop() ? context.pop() : context.go(RoutePaths.store);
  }

  ShippingInput _shipping() => ShippingInput(
    recipientName: _recipientName.text.trim(),
    recipientPhone: _recipientPhone.text.trim(),
    postalCode: _postalCode.text.trim(),
    address1: _address1.text.trim(),
    address2: _address2.text.trim(),
  );

  Future<void> _submit(Product product) async {
    final isGoods = product.type == 'goods';
    final shipping = isGoods ? _shipping() : null;
    if (shipping != null && !shipping.isComplete) {
      setState(() => _errorText = '배송지를 모두 입력해 주세요.');
      return;
    }
    setState(() {
      _submitting = true;
      _errorText = null;
    });
    try {
      final order = await ref
          .read(checkoutRepositoryProvider)
          .placeOrder(
            productId: widget.productId,
            qty: widget.qty,
            option: widget.option,
            shipping: shipping,
            idempotencyKey: _idempotencyKey,
          );
      if (!mounted) return;
      setState(() => _placed = order);
    } on CheckoutAuthRequiredException {
      if (mounted) context.go(RoutePaths.login);
    } on CheckoutRejectedException catch (error) {
      if (mounted) setState(() => _errorText = error.message);
    } on PaymentUnavailableException {
      if (mounted) setState(() => _errorText = '결제가 준비 중이에요. 잠시 후 다시 시도해 주세요.');
    } on Exception {
      if (mounted) setState(() => _errorText = '주문을 완료하지 못했어요. 다시 시도해 주세요.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final placed = _placed;
    if (placed != null) {
      return _ConfirmationScaffold(order: placed);
    }
    final product = ref.watch(checkoutProductProvider(widget.productId));
    return Scaffold(
      appBar: AssenAppBar(title: '결제', onBack: () => _back(context)),
      body: AssenAsyncView<Product>(
        value: product,
        loading: const _CheckoutSkeleton(),
        onRetry: () =>
            ref.invalidate(checkoutProductProvider(widget.productId)),
        errorBuilder: (error, _) => error is ProductNotFoundException
            ? AssenEmptyState(
                title: '없는 상품이에요',
                message: '요청하신 상품이 없거나 판매가 종료되었어요.',
                actionLabel: '스토어로',
                onAction: () => context.go(RoutePaths.store),
              )
            : null,
        data: _buildBody,
      ),
    );
  }

  Widget _buildBody(Product product) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final isGoods = product.type == 'goods';
    final total = product.price * widget.qty;
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      children: [
        const AssenSectionHeader(title: '주문 상품'),
        _SummaryCard(product: product, qty: widget.qty, option: widget.option),
        const SizedBox(height: SpacingTokens.s5),

        if (isGoods) ...[
          const AssenSectionHeader(title: '배송지'),
          _ShippingForm(
            recipientName: _recipientName,
            recipientPhone: _recipientPhone,
            postalCode: _postalCode,
            address1: _address1,
            address2: _address2,
          ),
          const SizedBox(height: SpacingTokens.s5),
        ],

        const AssenSectionHeader(title: '결제 금액'),
        AssenCard(
          child: Row(
            children: [
              Text(
                '총 결제 금액',
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
              const Spacer(),
              Text(
                '₩${formatThousands(total)}',
                style: TextStyle(
                  fontSize: TypographyTokens.titleMSize,
                  fontWeight: FontWeight.w700,
                  color: colors.ink900,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: SpacingTokens.s2),
        const AssenNoticeBar(
          message: '실제 결제가 진행되지 않는 테스트 결제예요. 카드 정보는 요구하지 않아요.',
        ),

        if (_errorText != null) ...[
          const SizedBox(height: SpacingTokens.s3),
          Text(
            _errorText!,
            style: TextStyle(
              fontSize: TypographyTokens.bodySSize,
              color: colors.redMain,
            ),
          ),
        ],

        const SizedBox(height: SpacingTokens.s5),
        _PayAction(
          total: total,
          submitting: _submitting,
          onPay: () => _submit(product),
        ),
      ],
    );
  }
}

/// The pay action, gated on [paymentAvailableProvider]: a pay button when the
/// rail is open, else a "준비 중" notice (fail-closed).
class _PayAction extends ConsumerWidget {
  const _PayAction({
    required this.total,
    required this.submitting,
    required this.onPay,
  });

  final int total;
  final bool submitting;
  final VoidCallback onPay;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final available = ref.watch(paymentAvailableProvider);
    return available.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, _) =>
          const AssenNoticeBar(message: '결제 수단이 준비 중이에요. 곧 이용하실 수 있어요.'),
      data: (isOpen) => isOpen
          ? AssenButton(
              label: '₩${formatThousands(total)} 결제하기 (테스트)',
              expand: true,
              onPressed: submitting ? null : onPay,
            )
          : const AssenNoticeBar(
              message: '결제 수단이 준비 중이에요. 곧 이용하실 수 있어요.',
            ),
    );
  }
}

/// The order summary card: title + option over quantity and unit price.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.product,
    required this.qty,
    required this.option,
  });

  final Product product;
  final int qty;
  final String option;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return AssenCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            product.title,
            style: TextStyle(
              fontSize: TypographyTokens.titleMSize,
              fontWeight: FontWeight.w600,
              color: colors.ink900,
            ),
          ),
          if (option.isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.s1),
            Text(
              option,
              style: TextStyle(
                fontSize: TypographyTokens.bodySSize,
                color: colors.ink500,
              ),
            ),
          ],
          const SizedBox(height: SpacingTokens.s3),
          Row(
            children: [
              Text(
                '${product.priceLabel} × $qty',
                style: TextStyle(
                  fontSize: TypographyTokens.bodyMSize,
                  color: colors.ink600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// The delivery-address form for a goods order (5 fields; recipient/phone/postal/
/// street are required, detail line optional).
class _ShippingForm extends StatelessWidget {
  const _ShippingForm({
    required this.recipientName,
    required this.recipientPhone,
    required this.postalCode,
    required this.address1,
    required this.address2,
  });

  final TextEditingController recipientName;
  final TextEditingController recipientPhone;
  final TextEditingController postalCode;
  final TextEditingController address1;
  final TextEditingController address2;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AssenTextField(label: '받는 분', controller: recipientName),
        const SizedBox(height: SpacingTokens.s3),
        AssenTextField(
          label: '연락처',
          controller: recipientPhone,
          keyboardType: TextInputType.phone,
        ),
        const SizedBox(height: SpacingTokens.s3),
        AssenTextField(
          label: '우편번호',
          controller: postalCode,
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: SpacingTokens.s3),
        AssenTextField(label: '주소', controller: address1),
        const SizedBox(height: SpacingTokens.s3),
        AssenTextField(
          label: '상세 주소 (선택)',
          controller: address2,
        ),
      ],
    );
  }
}

/// The post-order confirmation: a success message + links to the order/store.
class _ConfirmationScaffold extends StatelessWidget {
  const _ConfirmationScaffold({required this.order});

  final Order order;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    return Scaffold(
      appBar: const AssenAppBar(title: '주문 완료'),
      body: Padding(
        padding: const EdgeInsets.all(SpacingTokens.s6),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Icon(Icons.check_circle, size: 64, color: colors.indigo500),
            const SizedBox(height: SpacingTokens.s4),
            Text(
              '주문이 완료되었어요',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: TypographyTokens.titleLSize,
                fontWeight: FontWeight.w800,
                color: colors.ink900,
              ),
            ),
            const SizedBox(height: SpacingTokens.s2),
            Text(
              '${order.totalLabel} · 주문번호 ${order.id}',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: TypographyTokens.bodyMSize,
                color: colors.ink600,
              ),
            ),
            const SizedBox(height: SpacingTokens.s8),
            AssenButton(
              label: '주문 상세 보기',
              expand: true,
              onPressed: () => context.go(RoutePaths.orderDetail(order.id)),
            ),
            const SizedBox(height: SpacingTokens.s3),
            AssenButton(
              label: '쇼핑 계속하기',
              style: AssenButtonStyle.secondary,
              expand: true,
              onPressed: () => context.go(RoutePaths.store),
            ),
          ],
        ),
      ),
    );
  }
}

/// The loading state: a summary-card-shaped skeleton.
class _CheckoutSkeleton extends StatelessWidget {
  const _CheckoutSkeleton();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.all(SpacingTokens.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AssenSkeleton(width: 100),
          SizedBox(height: SpacingTokens.s3),
          AssenSkeleton(width: double.infinity, height: 80),
          SizedBox(height: SpacingTokens.s5),
          AssenSkeleton(width: double.infinity, height: 52),
        ],
      ),
    );
  }
}
