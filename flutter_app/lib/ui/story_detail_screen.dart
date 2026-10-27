import 'package:flutter/material.dart';

import '../data/repository.dart';
import '../models.dart';
import 'ai_analysis_screen.dart';
import 'common.dart';

/// Screen 2: overview plus clearly separated button groups.
class StoryDetailScreen extends StatefulWidget {
  const StoryDetailScreen({super.key, required this.repository, required this.storyId, this.initialHeadline});
  final NewsRepository repository;
  final String storyId;
  final String? initialHeadline;

  @override
  State<StoryDetailScreen> createState() => _StoryDetailScreenState();
}

class _StoryDetailScreenState extends State<StoryDetailScreen> {
  Loaded<StoryDetail>? _loaded;
  ApiException? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final loaded = await widget.repository.fetchStory(widget.storyId);
      if (!mounted) return;
      setState(() {
        _loaded = loaded;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(),
        title: const Text('Story'),
        actions: [
          IconButton(tooltip: 'Refresh story', onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: AnimatedSwitcher(duration: const Duration(milliseconds: 250), child: _body(context)),
    );
  }

  Widget _body(BuildContext context) {
    if (_loading && _loaded == null) {
      return const Center(key: ValueKey('loading'), child: CircularProgressIndicator());
    }
    if (_loaded == null) {
      final gone = _error?.notFound ?? false;
      return MessageView(
        key: const ValueKey('error'),
        icon: gone ? Icons.history_toggle_off : Icons.cloud_off,
        title: gone ? 'Story no longer available' : 'Can’t load this story',
        message: _error?.message ?? 'Something went wrong.',
        actionLabel: gone ? 'Back to stories' : 'Try again',
        onAction: gone ? () => Navigator.of(context).maybePop() : _load,
      );
    }
    final loaded = _loaded!;
    final story = loaded.data;
    final theme = Theme.of(context);
    final publishers = story.publishers;

    return RefreshIndicator(
      key: const ValueKey('detail'),
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          if (loaded.fromCache)
            StatusBanner(
              kind: BannerKind.offline,
              text: 'Offline: saved ${formatWhen(loaded.syncedAt)}. Publisher and background pages need internet.',
              actionLabel: 'Retry',
              onAction: _load,
            ),
          Text(story.headline,
              style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700, height: 1.25)),
          const SizedBox(height: 8),
          Text(
            '${plural(publishers.length, 'publisher')} · ${plural(story.articles.length, 'article')} · latest ${formatWhen(story.latestPublishedAt)}',
            style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 16),
          _Overview(story: story),

          SectionHeader('Original coverage',
              icon: Icons.newspaper,
              subtitle: 'Each publisher’s own reporting, in its original wording. Opens in your browser.'),
          for (final p in publishers)
            ActionTile(
              leading: _PublisherAvatar(p.name),
              title: p.name,
              subtitle: p.articles.length == 1
                  ? '${p.articles.first.title}\n${formatWhen(p.articles.first.publishedAt)}'
                  : '${plural(p.articles.length, 'article')} on this story',
              action: p.articles.length == 1 ? 'Open' : 'Choose',
              actionIcon: p.articles.length == 1 ? Icons.open_in_new : Icons.list,
              semanticsLabel: 'Open ${p.name} coverage',
              onTap: () => p.articles.length == 1
                  ? openLink(context, p.articles.first.url)
                  : _showArticleChooser(context, p),
            ),

          SectionHeader('Background', icon: Icons.menu_book, subtitle: 'Reference material selected by the server for this story.'),
          if (story.background.isEmpty)
            InfoCard(child: Text(story.backgroundMessage))
          else
            for (final b in story.background)
              ActionTile(
                leading: const Icon(Icons.public),
                title: b.title,
                subtitle: '${b.source}${b.description.isNotEmpty ? ' · ${b.description}' : ''}',
                semanticsLabel: 'Open background: ${b.title}',
                onTap: () => openLink(context, b.url),
              ),

          SectionHeader('AI analysis', icon: Icons.auto_awesome, subtitle: 'Generated on the server from the coverage above.'),
          ActionTile(
            leading: const AiBadge(text: 'AI'),
            title: 'Overview & perspectives',
            subtitle: _aiSubtitle(story.summary),
            action: 'View',
            actionIcon: Icons.chevron_right,
            onTap: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) => AiAnalysisScreen(story: story, fromCache: loaded.fromCache),
            )),
          ),
          const SizedBox(height: 16),
          Text(
            'Only publishers that covered this story are shown. Updated stories are collected hourly by the server.',
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }

  String _aiSubtitle(AiSummary s) {
    switch (s.status) {
      case 'ready':
        final n = s.content?.perspectives.length ?? 0;
        return 'Generated ${formatWhen(s.generatedAt)} · ${n >= 2 ? plural(n, 'perspective') : 'no distinct perspectives'}';
      case 'outdated':
        return 'Generated ${formatWhen(s.generatedAt)} · newer coverage pending';
      case 'failed':
        return 'Currently unavailable';
      default:
        return 'Not generated yet';
    }
  }

  void _showArticleChooser(BuildContext context, PublisherGroup p) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * 0.75),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              Text('${p.name} coverage', style: Theme.of(ctx).textTheme.titleLarge),
              const SizedBox(height: 12),
              for (final a in p.articles)
                ActionTile(
                  title: a.title,
                  subtitle: formatWhen(a.publishedAt),
                  onTap: () {
                    Navigator.of(ctx).pop();
                    openLink(context, a.url);
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Overview extends StatelessWidget {
  const _Overview({required this.story});
  final StoryDetail story;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final s = story.summary;
    final content = s.content;
    if (content != null && content.overview.isNotEmpty) {
      return InfoCard(
        tinted: true,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text('Story overview', style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 8),
            const AiBadge(),
          ]),
          const SizedBox(height: 8),
          Text(content.overview, style: theme.textTheme.bodyLarge?.copyWith(height: 1.4)),
          if (s.status == 'outdated')
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('Newer coverage has arrived; this overview will be refreshed by the next hourly run.',
                  style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF7A5200))),
            ),
        ]),
      );
    }
    // No AI text: show the newest publisher excerpt, clearly labelled as original wording.
    final withExcerpt = [...story.articles.where((a) => a.excerpt.isNotEmpty)]
      ..sort((a, b) => b.publishedAt.compareTo(a.publishedAt));
    return InfoCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Story overview', style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Text(s.statusMessage.isNotEmpty ? s.statusMessage : 'AI overview not available.',
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
        if (withExcerpt.isNotEmpty) ...[
          const SizedBox(height: 10),
          Text('Feed excerpt from ${withExcerpt.first.publisher} (original wording, not the full article):',
              style: theme.textTheme.labelMedium),
          const SizedBox(height: 4),
          Text('“${withExcerpt.first.excerpt}”', style: theme.textTheme.bodyMedium?.copyWith(height: 1.4)),
        ],
      ]),
    );
  }
}

class _PublisherAvatar extends StatelessWidget {
  const _PublisherAvatar(this.name);
  final String name;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final initials = name.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).take(2).map((w) => w[0]).join();
    return CircleAvatar(
      radius: 18,
      backgroundColor: cs.primaryContainer,
      child: Text(initials, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: cs.onPrimaryContainer)),
    );
  }
}
