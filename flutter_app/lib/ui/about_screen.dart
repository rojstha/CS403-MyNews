import 'package:flutter/material.dart';

import '../config.dart';
import 'common.dart';

/// Release notes, limitations and how beta testers report problems.
class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(leading: const BackButton(), title: const Text('About My News')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          Text('My News ${AppConfig.appVersion} (beta)', style: theme.textTheme.titleLarge),
          const SizedBox(height: 12),
          const InfoCard(
            title: 'How it works',
            child: Text(
              'A server collects news feeds every hour, groups articles about the same event into one story, '
              'finds background material and writes an AI analysis once. Every reader sees the same stored results; '
              'this app only reads them.',
            ),
          ),
          const InfoCard(
            title: 'Limitations',
            child: Text(
              '• AI analysis uses headlines and short feed excerpts, not full articles, and can be wrong. '
              'Check the original coverage.\n'
              '• Stories older than seven days are removed.\n'
              '• Grouping is automatic and can occasionally split one event or combine related ones.\n'
              '• Publisher and Wikipedia pages open in your browser and need an internet connection.',
            ),
          ),
          InfoCard(
            title: 'Report a problem',
            child: Text(
              AppConfig.feedbackEmail.isNotEmpty
                  ? 'Email ${AppConfig.feedbackEmail} with what you tapped, what you expected, and a screenshot.'
                  : 'Use the beta feedback form or issue tracker shared with your invitation. '
                      'Include what you tapped, what you expected, and a screenshot.',
            ),
          ),
          Text('Server: ${AppConfig.apiBaseUrl}', style: theme.textTheme.bodySmall),
          if (AppConfig.feedbackEmail.isNotEmpty)
            TextButton(
              onPressed: () => openLink(context, 'mailto:${AppConfig.feedbackEmail}'),
              child: const Text('Send feedback'),
            ),
        ],
      ),
    );
  }
}
