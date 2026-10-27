import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models.dart';

// ---------------------------------------------------------------- formatting

/// "Today, 9:40 AM", "Yesterday, 6:05 PM", "Mon, Oct 26, 8:15 AM" in local time.
String formatWhen(DateTime? utc, {DateTime? now}) {
  if (utc == null) return 'unknown time';
  final t = utc.toLocal();
  final n = (now ?? DateTime.now()).toLocal();
  final today = DateTime(n.year, n.month, n.day);
  final day = DateTime(t.year, t.month, t.day);
  final time = DateFormat.jm().format(t);
  final diff = today.difference(day).inDays;
  if (diff == 0) return 'Today, $time';
  if (diff == 1) return 'Yesterday, $time';
  return '${DateFormat('EEE, MMM d').format(t)}, $time';
}

String plural(int n, String word, [String? pluralWord]) => '$n ${n == 1 ? word : (pluralWord ?? '${word}s')}';

// ---------------------------------------------------------------- links

/// Opens a publisher or background page in the browser. The page itself is
/// not served by My News and needs an internet connection.
Future<void> openLink(BuildContext context, String url) async {
  final uri = Uri.tryParse(url);
  var ok = false;
  if (uri != null && (uri.scheme == 'https' || uri.scheme == 'http')) {
    try {
      ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      ok = false;
    }
  }
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Could not open the link. Publisher pages need an internet connection.')),
    );
  }
}

// ---------------------------------------------------------------- building blocks

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.subtitle, this.icon});
  final String title;
  final String? subtitle;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 24, 4, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            if (icon != null) ...[Icon(icon, size: 20, color: theme.colorScheme.primary), const SizedBox(width: 8)],
            Expanded(
              child: Text(title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: theme.colorScheme.primary,
                  )),
            ),
          ]),
          if (subtitle != null)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(subtitle!, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            ),
        ],
      ),
    );
  }
}

/// A large, easy-to-tap row: title, optional subtitle, trailing action word.
class ActionTile extends StatelessWidget {
  const ActionTile({
    super.key,
    required this.title,
    this.subtitle,
    this.leading,
    this.action = 'Open',
    this.actionIcon = Icons.open_in_new,
    required this.onTap,
    this.semanticsLabel,
  });

  final String title;
  final String? subtitle;
  final Widget? leading;
  final String action;
  final IconData actionIcon;
  final VoidCallback onTap;
  final String? semanticsLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: theme.colorScheme.surfaceContainerLowest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: theme.colorScheme.outlineVariant),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Semantics(
            button: true,
            label: semanticsLabel,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 56),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(
                  children: [
                    if (leading != null) ...[leading!, const SizedBox(width: 12)],
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
                          if (subtitle != null && subtitle!.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 3),
                              child: Text(
                                subtitle!,
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Row(mainAxisSize: MainAxisSize.min, children: [
                      Text(action,
                          style: theme.textTheme.labelLarge
                              ?.copyWith(color: theme.colorScheme.primary, fontWeight: FontWeight.w700)),
                      const SizedBox(width: 4),
                      Icon(actionIcon, size: 18, color: theme.colorScheme.primary),
                    ]),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class InfoCard extends StatelessWidget {
  const InfoCard({super.key, this.title, required this.child, this.tinted = false});
  final String? title;
  final Widget child;
  final bool tinted;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      color: tinted ? theme.colorScheme.secondaryContainer.withValues(alpha: 0.45) : theme.colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null) ...[
              Text(title!, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
            ],
            child,
          ],
        ),
      ),
    );
  }
}

enum BannerKind { info, warning, error, offline }

class StatusBanner extends StatelessWidget {
  const StatusBanner({super.key, required this.kind, required this.text, this.actionLabel, this.onAction});
  final BannerKind kind;
  final String text;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final (Color bg, Color fg, IconData icon) = switch (kind) {
      BannerKind.info => (cs.primaryContainer, cs.onPrimaryContainer, Icons.info_outline),
      BannerKind.warning => (const Color(0xFFFFF1D6), const Color(0xFF5C3B00), Icons.schedule),
      BannerKind.error => (cs.errorContainer, cs.onErrorContainer, Icons.error_outline),
      BannerKind.offline => (const Color(0xFFE8EAF0), const Color(0xFF2A3245), Icons.cloud_off),
    };
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          Icon(icon, color: fg, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: TextStyle(color: fg, height: 1.3))),
          if (actionLabel != null && onAction != null)
            TextButton(
              onPressed: onAction,
              style: TextButton.styleFrom(foregroundColor: fg, minimumSize: const Size(48, 44)),
              child: Text(actionLabel!, style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
        ],
      ),
    );
  }
}

class AiBadge extends StatelessWidget {
  const AiBadge({super.key, this.text = 'AI-generated'});
  final String text;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: cs.tertiaryContainer, borderRadius: BorderRadius.circular(20)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.auto_awesome, size: 14, color: cs.onTertiaryContainer),
        const SizedBox(width: 4),
        Flexible(
          child: Text(text,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: cs.onTertiaryContainer)),
        ),
      ]),
    );
  }
}

/// Full-screen message with an optional retry, used for error and empty states.
class MessageView extends StatelessWidget {
  const MessageView({super.key, required this.icon, required this.title, required this.message, this.actionLabel, this.onAction});
  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 56, color: theme.colorScheme.outline),
            const SizedBox(height: 16),
            Text(title, textAlign: TextAlign.center, style: theme.textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(message,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 20),
              FilledButton.icon(onPressed: onAction, icon: const Icon(Icons.refresh), label: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

/// Pulsing placeholder cards shown while the story list loads.
class SkeletonList extends StatefulWidget {
  const SkeletonList({super.key, this.count = 6});
  final int count;
  @override
  State<SkeletonList> createState() => _SkeletonListState();
}

class _SkeletonListState extends State<SkeletonList> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).colorScheme.surfaceContainerHighest;
    Widget bar(double w, double h) => Container(
          width: w,
          height: h,
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(color: base, borderRadius: BorderRadius.circular(6)),
        );
    return Semantics(
      label: 'Loading stories',
      child: FadeTransition(
        opacity: Tween(begin: 0.45, end: 1.0).animate(_c),
        child: ListView.builder(
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          itemCount: widget.count,
          itemBuilder: (_, _) => Card(
            elevation: 0,
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: LayoutBuilder(
                builder: (_, c) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  bar(c.maxWidth, 16),
                  bar(c.maxWidth * 0.7, 16),
                  const SizedBox(height: 6),
                  bar(c.maxWidth * 0.45, 12),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Small numbered citation chips, e.g. [1] [3], that open the cited article.
class CitationRow extends StatelessWidget {
  const CitationRow({super.key, required this.articleIds, required this.numbering, required this.story});
  final List<String> articleIds;
  final Map<String, int> numbering;
  final StoryDetail story;

  @override
  Widget build(BuildContext context) {
    final ids = articleIds.where(numbering.containsKey).toList()..sort((a, b) => numbering[a]!.compareTo(numbering[b]!));
    if (ids.isEmpty) return const SizedBox.shrink();
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Text('Sources:', style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
          for (final id in ids)
            ActionChip(
              visualDensity: VisualDensity.compact,
              tooltip: story.articleById(id)?.publisher,
              label: Text('[${numbering[id]}] ${story.articleById(id)?.publisher ?? ''}'),
              onPressed: () {
                final a = story.articleById(id);
                if (a != null) openLink(context, a.url);
              },
            ),
        ],
      ),
    );
  }
}

/// Stable [n] numbering of a story's articles (oldest first), shared by the AI screens.
Map<String, int> citationNumbers(StoryDetail story) {
  final sorted = [...story.articles]..sort((a, b) {
      final c = a.publishedAt.compareTo(b.publishedAt);
      return c != 0 ? c : a.id.compareTo(b.id);
    });
  return {for (var i = 0; i < sorted.length; i++) sorted[i].id: i + 1};
}
