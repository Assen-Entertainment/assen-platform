import 'dart:async';

import 'package:assen_mobile/src/app/router.dart';
import 'package:assen_mobile/src/common/async_view.dart';
import 'package:assen_mobile/src/discovery/creator.dart';
import 'package:assen_mobile/src/search/search_controller.dart';
import 'package:assen_mobile/src/search/search_result.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:core_tokens/core_tokens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:ui_kit/ui_kit.dart';

/// How long to wait after the last keystroke before firing a search.
const Duration _debounce = Duration(milliseconds: 300);

/// The search tab: a debounced field over `GET /api/search?q=`.
///
/// Renders every state through ui_kit only — a guidance empty state for a blank
/// query, a skeleton while the debounce/request is in flight, [AssenErrorState]
/// (with retry) on failure, a "결과 없음" empty state when nothing matches, and
/// otherwise a creators + products result list. Tapping a creator opens the
/// deep-linkable profile.
class SearchScreen extends ConsumerStatefulWidget {
  /// Creates the search tab.
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final TextEditingController _controller = TextEditingController();
  Timer? _debounceTimer;
  String _query = '';

  /// True while a debounce timer is pending, so the screen shows the skeleton
  /// instead of flashing "no results" before the request fires.
  bool _pending = false;

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    _debounceTimer?.cancel();
    setState(() => _query = value);
    if (value.trim().isEmpty) {
      _pending = false;
      ref.read(searchControllerProvider.notifier).search('');
      return;
    }
    setState(() => _pending = true);
    _debounceTimer = Timer(_debounce, () {
      if (!mounted) return;
      setState(() => _pending = false);
      ref.read(searchControllerProvider.notifier).search(value);
    });
  }

  @override
  Widget build(BuildContext context) {
    final results = ref.watch(searchControllerProvider);
    final query = _query.trim();

    return Scaffold(
      appBar: const AssenAppBar(title: '검색'),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(SpacingTokens.s4),
            child: AssenSearchField(
              controller: _controller,
              hintText: '크리에이터·상품 검색',
              onChanged: _onChanged,
              onClear: () => _onChanged(''),
            ),
          ),
          Expanded(child: _body(query, results)),
        ],
      ),
    );
  }

  Widget _body(String query, AsyncValue<SearchResult> results) {
    if (query.isEmpty) {
      return const AssenEmptyState(
        title: '무엇을 찾고 있나요?',
        message: '크리에이터 이름이나 상품을 검색해 보세요.',
      );
    }
    if (_pending) return const _SearchSkeleton();
    return AssenAsyncView<SearchResult>(
      value: results,
      loading: const _SearchSkeleton(),
      errorTitle: '검색하지 못했어요',
      onRetry: () => ref.read(searchControllerProvider.notifier).search(query),
      isEmpty: (result) => result.isEmpty,
      empty: () => AssenEmptyState(
        title: '결과가 없어요',
        message: '"$query"와 일치하는 크리에이터나 상품이 없어요.',
      ),
      data: (result) => _SearchResults(result: result),
    );
  }
}

/// The loaded results: a creators section and a products section.
class _SearchResults extends StatelessWidget {
  const _SearchResults({required this.result});

  final SearchResult result;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(
        SpacingTokens.s4,
        0,
        SpacingTokens.s4,
        SpacingTokens.s8,
      ),
      children: [
        if (result.creators.isNotEmpty) ...[
          const AssenSectionHeader(title: '크리에이터'),
          for (final creator in result.creators)
            _CreatorResult(creator: creator),
        ],
        if (result.products.isNotEmpty) ...[
          const SizedBox(height: SpacingTokens.s4),
          const AssenSectionHeader(title: '상품'),
          const SizedBox(height: SpacingTokens.s3),
          for (final product in result.products) ...[
            AssenProductCard(
              title: product.title,
              priceLabel: product.priceLabel,
              tagLabel: product.typeLabel,
              meta: product.meta,
            ),
            const SizedBox(height: SpacingTokens.s3),
          ],
        ],
      ],
    );
  }
}

/// A single creator search hit, opening the profile on tap.
class _CreatorResult extends StatelessWidget {
  const _CreatorResult({required this.creator});

  final Creator creator;

  @override
  Widget build(BuildContext context) {
    return AssenListItem(
      title: creator.displayName,
      subtitle:
          '@${creator.handle}'
          '${creator.category == null ? '' : ' · ${creator.category}'}',
      leading: AssenAvatar(
        name: creator.displayName,
        imageProvider: creator.avatarUrl == null
            ? null
            : CachedNetworkImageProvider(creator.avatarUrl!),
        semanticLabel: '${creator.displayName} 프로필 사진',
      ),
      onTap: () => context.go(RoutePaths.creator(creator.handle)),
    );
  }
}

/// The loading state: a few skeleton rows standing in for results.
class _SearchSkeleton extends StatelessWidget {
  const _SearchSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(SpacingTokens.s4),
      itemCount: 6,
      itemBuilder: (context, index) => const Padding(
        padding: EdgeInsets.symmetric(vertical: SpacingTokens.s3),
        child: Row(
          children: [
            AssenSkeleton(width: 48, height: 48, radius: 24),
            SizedBox(width: SpacingTokens.s3),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AssenSkeleton(width: 140),
                  SizedBox(height: SpacingTokens.s2),
                  AssenSkeleton(width: 200),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
