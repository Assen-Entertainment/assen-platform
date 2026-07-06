import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/notifications/app_notification.dart';
import 'package:assen_mobile/src/notifications/notifications_controller.dart';
import 'package:assen_mobile/src/notifications/notifications_repository.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// The 알림 tab: the signed-in fan's notification feed.
///
/// Wired to `GET /api/notifications` through
/// [notificationsControllerProvider]. Because the app ships signed-out, the
/// default path is a 401 → [NotificationsAuthRequiredException], which this
/// screen renders as a "로그인이 필요해요" empty state (with a login CTA) rather than
/// an error. When authenticated it shows the list (read/unread + relative
/// time); other failures fall back to [AssenErrorState] with retry.
class NotificationsScreen extends ConsumerWidget {
  /// Creates the notifications tab.
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final feed = ref.watch(notificationsControllerProvider);
    return Scaffold(
      appBar: const AssenAppBar(title: '알림'),
      body: feed.when(
        loading: () => const _NotificationsSkeleton(),
        error: (error, stackTrace) =>
            error is NotificationsAuthRequiredException
            ? AssenEmptyState(
                title: '로그인이 필요해요',
                message: '알림을 보려면 먼저 로그인해 주세요.',
                actionLabel: '로그인',
                onAction: () => context.go(RoutePaths.login),
              )
            : AssenErrorState(
                title: '불러오지 못했어요',
                message: '네트워크 상태를 확인하고 다시 시도해 주세요.',
                onRetry: () => ref
                    .read(notificationsControllerProvider.notifier)
                    .refresh(),
              ),
        data: (items) => items.isEmpty
            ? const AssenEmptyState(
                title: '알림이 없어요',
                message: '새로운 소식이 도착하면 이곳에 표시됩니다.',
              )
            : _NotificationList(items: items),
      ),
    );
  }
}

/// The loaded feed: a list of notifications, newest first.
class _NotificationList extends StatelessWidget {
  const _NotificationList({required this.items});

  final List<AppNotification> items;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.s2),
      itemCount: items.length,
      itemBuilder: (context, index) =>
          _NotificationTile(notification: items[index], now: now),
    );
  }
}

/// One notification row: a bell (rose-tinted when unread) + title + time.
class _NotificationTile extends StatelessWidget {
  const _NotificationTile({required this.notification, required this.now});

  final AppNotification notification;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<AssenColors>()!;
    final unread = !notification.read;

    return AssenListItem(
      title: notification.title,
      subtitle: _relativeTime(notification.createdAt, now),
      showChevron: false,
      leading: Container(
        width: SpacingTokens.s10,
        height: SpacingTokens.s10,
        decoration: BoxDecoration(
          color: unread ? colors.strawberryBg : colors.cream200,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(
          Icons.notifications_none,
          size: SpacingTokens.s5,
          color: unread ? colors.strawberryInk : colors.ink500,
        ),
      ),
      trailing: unread
          ? Container(
              width: SpacingTokens.s2,
              height: SpacingTokens.s2,
              decoration: BoxDecoration(
                color: colors.roseMain,
                shape: BoxShape.circle,
              ),
            )
          : null,
    );
  }
}

/// The loading state: skeleton rows standing in for the feed.
class _NotificationsSkeleton extends StatelessWidget {
  const _NotificationsSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 6,
      itemBuilder: (context, index) => const Padding(
        padding: EdgeInsets.symmetric(vertical: SpacingTokens.s3),
        child: Row(
          children: [
            AssenSkeleton(width: 40, height: 40, radius: 20),
            SizedBox(width: SpacingTokens.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AssenSkeleton(width: 200),
                  SizedBox(height: SpacingTokens.s2),
                  AssenSkeleton(width: 80),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Formats [time] relative to [now] (방금 전 / N분 전 / N시간 전 / N일 전 / 날짜).
String _relativeTime(DateTime time, DateTime now) {
  final diff = now.difference(time);
  if (diff.inMinutes < 1) return '방금 전';
  if (diff.inMinutes < 60) return '${diff.inMinutes}분 전';
  if (diff.inHours < 24) return '${diff.inHours}시간 전';
  if (diff.inDays < 7) return '${diff.inDays}일 전';
  return '${time.year}.${_two(time.month)}.${_two(time.day)}';
}

/// Zero-pads a month/day to two digits.
String _two(int value) => value.toString().padLeft(2, '0');
