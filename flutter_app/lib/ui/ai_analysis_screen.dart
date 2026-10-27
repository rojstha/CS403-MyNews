import 'package:flutter/material.dart';

import '../models.dart';
import 'common.dart';
import 'perspective_screen.dart';

/// Screen 3: the stored AI analysis for one story. Reading it never triggers
/// generation; the server's hourly job produces it once for all readers.
class AiAnalysisScreen extends StatelessWidget {
  const AiAnalysisScreen({super.key, required this.story, this.fromCache = false});
  final StoryDetail story;
  final bool fromCache;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final s = story.summary;
    final content = s.content;
    final numbers = citationNumbers(story);

    return Scaffold(
      appBar: AppBar(leading: const BackButton(), title: const Text('AI analysis')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text(story.headline, style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
            const AiBadge(),
            if (s.generatedAt != null || s.model != null)
              Text(
                [
                  if (s.generatedAt != null) 'Generated ${formatWhen(s.generatedAt)}',
                  if (s.model != null) 'model ${s.model}',
                ].join(' · '),
                style: theme.textTheme.bodySmall,
              ),
          ]),
          const SizedBox(height: 12),
          if (s.status == 'outdated')
            const StatusBanner(
              kind: BannerKind.warning,
              text: 'Outdated: newer coverage arrived after this analysis was generated. '
                  'It still only cites articles listed below and will be refreshed by the next hourly run.',
            ),
          if (fromCache)
            const StatusBanner(kind: BannerKind.offline, text: 'Offline: showing the analysis saved on this phone.'),
          if (content == null) ...[
            StatusBanner(
              kind: s.status == 'failed' ? BannerKind.error : BannerKind.info,
              text: s.statusMessage.isNotEmpty ? s.statusMessage : 'AI analysis is not available for this story.',
            ),
            InfoCard(
              child: Text(
                'No AI text is shown rather than an unverified substitute. '
                'The original coverage is still available from the story screen.',
                style: theme.textTheme.bodyMedium,
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => Navigator.of(context).maybePop(),
              icon: const Icon(Icons.newspaper),
              label: const Text('Back to original coverage'),
              style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            ),
          ] else ...[
            InfoCard(
              title: 'Overview',
              tinted: true,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(content.overview, style: theme.textTheme.bodyLarge?.copyWith(height: 1.4)),
                CitationRow(articleIds: content.overviewArticleIds, numbering: numbers, story: story),
              ]),
            ),
            if (content.agreement.isNotEmpty)
              InfoCard(title: 'Where sources agree', child: Text(content.agreement, style: const TextStyle(height: 1.4))),
            if (content.disagreement.isNotEmpty)
              InfoCard(title: 'Differences between sources', child: Text(content.disagreement, style: const TextStyle(height: 1.4))),
            if (content.uncertainty.isNotEmpty)
              InfoCard(title: 'Uncertain or unknown', child: Text(content.uncertainty, style: const TextStyle(height: 1.4))),
            Text('Agreement among sources is not proof that a claim is true.',
                style: theme.textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic)),
            const SectionHeader('Explore perspectives', icon: Icons.forum_outlined),
            if (content.perspectivesSupported && content.perspectives.length >= 2)
              for (final p in content.perspectives)
                ActionTile(
                  title: p.name,
                  subtitle: p.summary,
                  action: 'View',
                  actionIcon: Icons.chevron_right,
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => PerspectiveScreen(story: story, perspective: p),
                  )),
                )
            else
              InfoCard(
                child: Text(
                  content.perspectivesNote.isNotEmpty
                      ? content.perspectivesNote
                      : 'Insufficient evidence for distinct perspectives.',
                ),
              ),
          ],
          SectionHeader('Supporting articles', icon: Icons.link,
              subtitle: content == null ? null : 'The articles the AI was given, numbered as cited above.'),
          for (final a in [...story.articles]..sort((x, y) => (numbers[x.id] ?? 0).compareTo(numbers[y.id] ?? 0)))
            ActionTile(
              title: '[${numbers[a.id]}] ${a.publisher}',
              subtitle: '${a.title}\n${formatWhen(a.publishedAt)}',
              onTap: () => openLink(context, a.url),
            ),
          const SizedBox(height: 8),
          Text(
            s.inputScopeNote.isNotEmpty
                ? s.inputScopeNote
                : 'Input scope: headlines and short feed excerpts only. Read the original coverage for full context.',
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ],
      ),
    );
  }
}
