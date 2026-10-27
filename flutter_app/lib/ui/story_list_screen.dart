import 'package:flutter/material.dart';

import '../data/repository.dart';
import '../models.dart';
import 'about_screen.dart';
import 'common.dart';
import 'story_detail_screen.dart';

enum DayFilter { all, today, yesterday, earlier }

/// Screen 1: one card per grouped story, newest first.
class StoryListScreen extends StatefulWidget {
  const StoryListScreen({super.key, required this.repository});
  final NewsRepository repository;

  @override
  State<StoryListScreen> createState() => _StoryListScreenState();
}

class _StoryListScreenState extends State<StoryListScreen> {
  Loaded<StoryList>? _loaded;
  String? _error;
  bool _loading = true;

  // Filters inspired by the starter app's source and day buttons. They only
  // filter what the server already returned.
  String? _publisher;
  bool _multiSourceOnly = false;
  DayFilter _day = DayFilter.all;

  @override
  void initState() {
    super.initState();
    _refresh();
    widget.repository.pruneCache();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final loaded = await widget.repository.fetchStories();
      if (!mounted) return;
      setState(() {
        _loaded = loaded;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  bool _matchesDay(DateTime utc) {
    if (_day == DayFilter.all) return true;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final t = utc.toLocal();
    final day = DateTime(t.year, t.month, t.day);
    final diff = today.difference(day).inDays;
    return switch (_day) {
      DayFilter.today => diff == 0,
      DayFilter.yesterday => diff == 1,
      DayFilter.earlier => diff >= 2,
      DayFilter.all => true,
    };
  }

  List<StorySummaryItem> get _visible {
    final stories = _loaded?.data.stories ?? const <StorySummaryItem>[];
    return stories.where((s) {
      if (_publisher != null && !s.publishers.contains(_publisher)) return false;
      if (_multiSourceOnly && s.publisherCount < 2) return false;
      return _matchesDay(s.latestPublishedAt);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My News'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _refresh,
          ),
          IconButton(
            tooltip: 'About and feedback',
            icon: const Icon(Icons.info_outline),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const AboutScreen())),
          ),
        ],
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 250),
        child: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading && _loaded == null) return const SkeletonList(key: ValueKey('loading'));
    if (_loaded == null) {
      return MessageView(
        key: const ValueKey('error'),
        icon: Icons.cloud_off,
        title: 'Can’t load stories',
        message: '${_error ?? 'Something went wrong.'}\n\nNo saved stories are available on this phone yet.',
        actionLabel: 'Try again',
        onAction: _refresh,
      );
    }

    final loaded = _loaded!;
    final visible = _visible;
    final publishers = {for (final s in loaded.data.stories) ...s.publishers}.toList()..sort();

    return RefreshIndicator(
      key: const ValueKey('list'),
      onRefresh: _refresh,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
            sliver: SliverList.list(children: [
              if (_loading) const LinearProgressIndicator(minHeight: 2),
              _Header(loaded: loaded),
              if (loaded.fromCache)
                StatusBanner(
                  kind: BannerKind.offline,
                  text: 'Offline: showing stories saved ${formatWhen(loaded.syncedAt)}. '
                      'Expired stories are hidden. Publisher links need internet.',
                  actionLabel: 'Retry',
                  onAction: _refresh,
                )
              else if (_error != null)
                StatusBanner(kind: BannerKind.error, text: _error!, actionLabel: 'Retry', onAction: _refresh),
              if (!loaded.fromCache && loaded.data.lastRun?.status == 'failed')
                const StatusBanner(
                  kind: BannerKind.warning,
                  text: 'The latest server collection could not reach the news sources. Showing the most recent stored stories.',
                ),
              _Filters(
                publishers: publishers,
                publisher: _publisher,
                multiSourceOnly: _multiSourceOnly,
                day: _day,
                onPublisher: (p) => setState(() => _publisher = p),
                onMultiSource: (v) => setState(() => _multiSourceOnly = v),
                onDay: (d) => setState(() => _day = d),
              ),
            ]),
          ),
          if (visible.isEmpty)
            SliverFillRemaining(
              hasScrollBody: false,
              child: MessageView(
                icon: Icons.inbox_outlined,
                title: loaded.data.stories.isEmpty ? 'No stories yet' : 'No matching stories',
                message: loaded.data.stories.isEmpty
                    ? 'The server has no stories from the last seven days yet. New coverage is collected every hour.'
                    : 'Try a different source or day filter.',
                actionLabel: loaded.data.stories.isEmpty ? 'Refresh' : 'Clear filters',
                onAction: loaded.data.stories.isEmpty
                    ? _refresh
                    : () => setState(() {
                          _publisher = null;
                          _multiSourceOnly = false;
                          _day = DayFilter.all;
                        }),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
              sliver: SliverList.builder(
                itemCount: visible.length + 1,
                itemBuilder: (context, i) {
                  if (i == visible.length) {
                    return Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text(
                        'Newest first · most recent seven days · ${plural(visible.length, 'story')}',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    );
                  }
                  return _StoryCard(
                    story: visible[i],
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => StoryDetailScreen(
                        repository: widget.repository,
                        storyId: visible[i].id,
                        initialHeadline: visible[i].headline,
                      ),
                    )),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.loaded});
  final Loaded<StoryList> loaded;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final last = loaded.data.lastSuccessfulCollectionAt;
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Top stories', style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text(
          last == null ? 'Server has not completed a collection yet' : 'Server updated ${formatWhen(last)}',
          style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant),
        ),
      ]),
    );
  }
}

class _Filters extends StatelessWidget {
  const _Filters({
    required this.publishers,
    required this.publisher,
    required this.multiSourceOnly,
    required this.day,
    required this.onPublisher,
    required this.onMultiSource,
    required this.onDay,
  });

  final List<String> publishers;
  final String? publisher;
  final bool multiSourceOnly;
  final DayFilter day;
  final ValueChanged<String?> onPublisher;
  final ValueChanged<bool> onMultiSource;
  final ValueChanged<DayFilter> onDay;

  @override
  Widget build(BuildContext context) {
    const dayLabels = {
      DayFilter.all: 'All days',
      DayFilter.today: 'Today',
      DayFilter.yesterday: 'Yesterday',
      DayFilter.earlier: 'Earlier',
    };
    return Column(children: [
      SizedBox(
        height: 48,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: [
            FilterChip(
              label: const Text('2+ sources'),
              selected: multiSourceOnly,
              onSelected: onMultiSource,
            ),
            const SizedBox(width: 8),
            ChoiceChip(label: const Text('All sources'), selected: publisher == null, onSelected: (_) => onPublisher(null)),
            for (final p in publishers) ...[
              const SizedBox(width: 8),
              ChoiceChip(label: Text(p), selected: publisher == p, onSelected: (_) => onPublisher(publisher == p ? null : p)),
            ],
          ],
        ),
      ),
      SizedBox(
        height: 48,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: [
            for (final d in DayFilter.values) ...[
              ChoiceChip(label: Text(dayLabels[d]!), selected: day == d, onSelected: (_) => onDay(d)),
              const SizedBox(width: 8),
            ],
          ],
        ),
      ),
      const SizedBox(height: 4),
    ]);
  }
}

class _StoryCard extends StatelessWidget {
  const _StoryCard({required this.story, required this.onTap});
  final StorySummaryItem story;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final multi = story.publisherCount >= 2;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: cs.surfaceContainerLowest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: cs.outlineVariant),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(story.headline,
                  style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700, height: 1.25)),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: multi ? cs.primaryContainer : cs.surfaceContainerHigh,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      plural(story.publisherCount, 'publisher'),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: multi ? cs.onPrimaryContainer : cs.onSurfaceVariant,
                      ),
                    ),
                  ),
                  Text(formatWhen(story.latestPublishedAt),
                      style: theme.textTheme.bodySmall?.copyWith(color: cs.onSurfaceVariant)),
                  if (story.summaryStatus == 'ready' || story.summaryStatus == 'outdated')
                    Icon(Icons.auto_awesome, size: 16, color: cs.tertiary, semanticLabel: 'AI analysis available'),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                story.publishers.join(' · '),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(color: cs.onSurfaceVariant),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

