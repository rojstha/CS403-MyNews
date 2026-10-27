import 'package:flutter/material.dart';

import '../models.dart';
import 'common.dart';

/// Screen 4: one AI-identified viewpoint with its claims and citations.
class PerspectiveScreen extends StatelessWidget {
  const PerspectiveScreen({super.key, required this.story, required this.perspective});
  final StoryDetail story;
  final Perspective perspective;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final numbers = citationNumbers(story);
    final others = story.summary.content?.perspectives.where((p) => p.name != perspective.name).toList() ?? const [];
    final supporting = perspective.articleIds.map(story.articleById).whereType<Article>().toList()
      ..sort((a, b) => numbers[a.id]!.compareTo(numbers[b.id]!));

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(),
        title: const Text('Perspective'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          const Align(alignment: Alignment.centerLeft, child: AiBadge(text: 'AI-generated · attributed viewpoint')),
          const SizedBox(height: 10),
          Text(perspective.name, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          if (perspective.summary.isNotEmpty)
            InfoCard(tinted: true, child: Text(perspective.summary, style: theme.textTheme.bodyLarge?.copyWith(height: 1.4))),
          const SectionHeader('Supported claims', icon: Icons.fact_check_outlined),
          for (final c in perspective.claims)
            InfoCard(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(c.text, style: const TextStyle(height: 1.4)),
                CitationRow(articleIds: c.articleIds, numbering: numbers, story: story),
              ]),
            ),
          if (perspective.limits.isNotEmpty)
            InfoCard(title: 'Evidence and limits', child: Text(perspective.limits, style: const TextStyle(height: 1.4))),
          const SectionHeader('Supporting coverage', icon: Icons.link),
          for (final a in supporting)
            ActionTile(
              title: '[${numbers[a.id]}] ${a.publisher}',
              subtitle: a.title,
              onTap: () => openLink(context, a.url),
            ),
          if (others.isNotEmpty) ...[
            const SectionHeader('Other perspectives', icon: Icons.swap_horiz),
            for (final p in others)
              ActionTile(
                title: p.name,
                action: 'Switch',
                actionIcon: Icons.swap_horiz,
                onTap: () => Navigator.of(context).pushReplacement(MaterialPageRoute(
                  builder: (_) => PerspectiveScreen(story: story, perspective: p),
                )),
              ),
          ],
          const SizedBox(height: 12),
          Text(
            'This viewpoint is reported by people or groups in the coverage. It is not assigned by publisher.',
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}
