// FIXTURE responses shaped like the real server's JSON (docs/API.md). Test-only.
import 'dart:convert';

final now = DateTime.utc(2026, 10, 27, 12);

String iso(DateTime t) => t.toUtc().toIso8601String();

Map<String, dynamic> storyListJson({List<Map<String, dynamic>>? stories, String lastRunStatus = 'success'}) => {
      'server_time': iso(now),
      'window_hours': 168,
      'ordering': 'newest_first',
      'last_successful_collection_at': iso(now.subtract(const Duration(minutes: 20))),
      'last_run': {'status': lastRunStatus, 'started_at': iso(now), 'finished_at': iso(now), 'feeds_ok': 13, 'feeds_failed': 0},
      'publishers': ['BBC News', 'NPR'],
      'count': (stories ?? defaultStories).length,
      'stories': stories ?? defaultStories,
    };

final defaultStories = [
  {
    'id': 's-old',
    'headline': 'Older story about a river project',
    'latest_published_at': iso(now.subtract(const Duration(hours: 160))),
    'publishers': ['NPR'],
    'article_count': 1,
    'article_dates': [
      {'publisher': 'NPR', 'published_at': iso(now.subtract(const Duration(hours: 160)))},
    ],
    'summary_status': 'pending',
    'has_background': false,
  },
  {
    'id': 's-new',
    'headline': 'Two charged over RAF Fairford plot',
    'latest_published_at': iso(now.subtract(const Duration(hours: 2))),
    'publishers': ['BBC News', 'NPR'],
    'article_count': 2,
    'article_dates': [
      {'publisher': 'NPR', 'published_at': iso(now.subtract(const Duration(hours: 165)))},
      {'publisher': 'BBC News', 'published_at': iso(now.subtract(const Duration(hours: 2)))},
    ],
    'summary_status': 'ready',
    'has_background': true,
  },
];

Map<String, dynamic> storyDetailJson({
  String status = 'ready',
  bool perspectives = true,
  bool background = true,
}) =>
    {
      'id': 's-new',
      'headline': 'Two charged over RAF Fairford plot',
      'updated_at': iso(now),
      'articles': [
        {
          'id': 'a1',
          'publisher': 'NPR',
          'title': 'NPR: two men charged',
          'url': 'https://npr.example/a1',
          'published_at': iso(now.subtract(const Duration(hours: 165))),
          'excerpt': 'Two men were charged.',
        },
        {
          'id': 'a2',
          'publisher': 'BBC News',
          'title': 'BBC: Two charged over alleged plot',
          'url': 'https://bbc.example/a2',
          'published_at': iso(now.subtract(const Duration(hours: 2))),
          'excerpt': 'Two men have been charged under the National Security Act.',
        },
      ],
      'background': background
          ? [
              {
                'title': 'RAF Fairford',
                'url': 'https://en.wikipedia.org/wiki/RAF_Fairford',
                'description': 'An air base in Gloucestershire.',
                'source': 'Wikipedia',
                'matched_term': 'RAF Fairford',
              }
            ]
          : [],
      'background_message': background ? '' : 'No background resource available',
      'last_successful_collection_at': iso(now),
      'summary': {
        'status': status,
        'status_message': status == 'failed' ? 'AI analysis is currently unavailable because the AI service failed.' : '',
        'label': 'AI-generated',
        'generated_at': status == 'ready' || status == 'outdated' ? iso(now) : null,
        'model': status == 'ready' || status == 'outdated' ? 'claude-opus-5-5' : null,
        'version': 1,
        'input_scope_note': 'Input scope: headlines and short feed excerpts only.',
        'input_article_ids': status == 'ready' || status == 'outdated' ? ['a1', 'a2'] : [],
        'content': status == 'ready' || status == 'outdated'
            ? {
                'overview': 'Two men were charged over an alleged plot, according to both sources.',
                'overview_article_ids': ['a1', 'a2'],
                'agreement': 'The sources agree two men were charged.',
                'disagreement': 'No meaningful disagreement is visible in the available coverage.',
                'uncertainty': 'The motive is not reported.',
                'perspectives_supported': perspectives,
                'perspectives_note': perspectives ? '' : 'Insufficient evidence for distinct perspectives. Only factual reporting.',
                'perspectives': perspectives
                    ? [
                        {
                          'name': 'Prosecutors',
                          'summary': 'Prosecutors say the men assisted Iran.',
                          'claims': [
                            {'text': 'They acted to assist Iran.', 'article_ids': ['a2']}
                          ],
                          'limits': 'Evidence has not been tested in court.',
                          'article_ids': ['a2'],
                        },
                        {
                          'name': 'Defence',
                          'summary': 'Lawyers deny the allegations.',
                          'claims': [
                            {'text': 'The men deny the charges.', 'article_ids': ['a1']}
                          ],
                          'limits': 'Only one source.',
                          'article_ids': ['a1'],
                        },
                      ]
                    : [],
              }
            : null,
      },
    };

String body(Map<String, dynamic> j) => jsonEncode(j);
