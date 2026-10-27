/// Plain data classes that mirror the server's JSON (see docs/API.md).
library;

DateTime? _date(dynamic v) =>
    v is String && v.isNotEmpty ? DateTime.tryParse(v)?.toUtc() : null;

List<T> _list<T>(dynamic v, T Function(Map<String, dynamic>) f) => v is List
    ? v.whereType<Map>().map((e) => f(Map<String, dynamic>.from(e))).toList()
    : <T>[];

List<String> _strings(dynamic v) =>
    v is List ? v.map((e) => e.toString()).toList() : <String>[];

String _s(dynamic v) => v?.toString() ?? '';

class ArticleDate {
  final String publisher;
  final DateTime publishedAt;
  ArticleDate(this.publisher, this.publishedAt);
}

class StorySummaryItem {
  final String id;
  final String headline;
  final DateTime latestPublishedAt;
  final List<String> publishers;
  final int articleCount;
  final String summaryStatus;
  final bool hasBackground;
  final List<ArticleDate> articleDates;

  StorySummaryItem({
    required this.id,
    required this.headline,
    required this.latestPublishedAt,
    required this.publishers,
    required this.articleCount,
    required this.summaryStatus,
    required this.hasBackground,
    required this.articleDates,
  });

  int get publisherCount => publishers.length;

  factory StorySummaryItem.fromJson(Map<String, dynamic> j) {
    final dates = <ArticleDate>[];
    for (final d in (j['article_dates'] as List? ?? const [])) {
      if (d is Map) {
        final t = _date(d['published_at']);
        if (t != null) dates.add(ArticleDate(_s(d['publisher']), t));
      }
    }
    return StorySummaryItem(
      id: _s(j['id']),
      headline: _s(j['headline']),
      latestPublishedAt: _date(j['latest_published_at']) ?? DateTime.utc(1970),
      publishers: _strings(j['publishers']),
      articleCount: (j['article_count'] as num?)?.toInt() ?? 0,
      summaryStatus: _s(j['summary_status']),
      hasBackground: j['has_background'] == true,
      articleDates: dates,
    );
  }

  /// A copy with expired articles removed, or null if nothing is left.
  /// Used only for cached (offline) data; the live server already filters.
  StorySummaryItem? withoutExpired(DateTime cutoff) {
    if (articleDates.isEmpty) {
      return latestPublishedAt.isBefore(cutoff) ? null : this;
    }
    final kept = articleDates.where((d) => !d.publishedAt.isBefore(cutoff)).toList();
    if (kept.isEmpty) return null;
    final pubs = kept.map((d) => d.publisher).toSet().toList()..sort();
    return StorySummaryItem(
      id: id,
      headline: headline,
      latestPublishedAt: kept.map((d) => d.publishedAt).reduce((a, b) => a.isAfter(b) ? a : b),
      publishers: pubs,
      articleCount: kept.length,
      summaryStatus: summaryStatus,
      hasBackground: hasBackground,
      articleDates: kept,
    );
  }
}

class CollectionRunInfo {
  final String status;
  final DateTime? startedAt;
  final DateTime? finishedAt;
  final int feedsOk;
  final int feedsFailed;

  CollectionRunInfo({
    required this.status,
    this.startedAt,
    this.finishedAt,
    required this.feedsOk,
    required this.feedsFailed,
  });

  factory CollectionRunInfo.fromJson(Map<String, dynamic> j) => CollectionRunInfo(
        status: _s(j['status']),
        startedAt: _date(j['started_at']),
        finishedAt: _date(j['finished_at']),
        feedsOk: (j['feeds_ok'] as num?)?.toInt() ?? 0,
        feedsFailed: (j['feeds_failed'] as num?)?.toInt() ?? 0,
      );
}

class StoryList {
  final DateTime? lastSuccessfulCollectionAt;
  final CollectionRunInfo? lastRun;
  final List<StorySummaryItem> stories;

  StoryList({this.lastSuccessfulCollectionAt, this.lastRun, required this.stories});

  factory StoryList.fromJson(Map<String, dynamic> j) {
    final stories = _list(j['stories'], StorySummaryItem.fromJson)
      ..sort((a, b) => b.latestPublishedAt.compareTo(a.latestPublishedAt));
    return StoryList(
      lastSuccessfulCollectionAt: _date(j['last_successful_collection_at']),
      lastRun: j['last_run'] is Map
          ? CollectionRunInfo.fromJson(Map<String, dynamic>.from(j['last_run']))
          : null,
      stories: stories,
    );
  }

  StoryList withoutExpired(DateTime cutoff) => StoryList(
        lastSuccessfulCollectionAt: lastSuccessfulCollectionAt,
        lastRun: lastRun,
        stories: stories.map((s) => s.withoutExpired(cutoff)).whereType<StorySummaryItem>().toList(),
      );
}

class Article {
  final String id;
  final String publisher;
  final String title;
  final String url;
  final DateTime publishedAt;
  final String excerpt;

  Article({
    required this.id,
    required this.publisher,
    required this.title,
    required this.url,
    required this.publishedAt,
    required this.excerpt,
  });

  factory Article.fromJson(Map<String, dynamic> j) => Article(
        id: _s(j['id']),
        publisher: _s(j['publisher']),
        title: _s(j['title']),
        url: _s(j['url']),
        publishedAt: _date(j['published_at']) ?? DateTime.utc(1970),
        excerpt: _s(j['excerpt']),
      );
}

class BackgroundResource {
  final String title;
  final String url;
  final String description;
  final String source;
  final String matchedTerm;

  BackgroundResource({
    required this.title,
    required this.url,
    required this.description,
    required this.source,
    required this.matchedTerm,
  });

  factory BackgroundResource.fromJson(Map<String, dynamic> j) => BackgroundResource(
        title: _s(j['title']),
        url: _s(j['url']),
        description: _s(j['description']),
        source: _s(j['source']),
        matchedTerm: _s(j['matched_term']),
      );
}

class Claim {
  final String text;
  final List<String> articleIds;
  Claim(this.text, this.articleIds);

  factory Claim.fromJson(Map<String, dynamic> j) => Claim(_s(j['text']), _strings(j['article_ids']));
}

class Perspective {
  final String name;
  final String summary;
  final List<Claim> claims;
  final String limits;
  final List<String> articleIds;

  Perspective({
    required this.name,
    required this.summary,
    required this.claims,
    required this.limits,
    required this.articleIds,
  });

  factory Perspective.fromJson(Map<String, dynamic> j) => Perspective(
        name: _s(j['name']),
        summary: _s(j['summary']),
        claims: _list(j['claims'], Claim.fromJson),
        limits: _s(j['limits']),
        articleIds: _strings(j['article_ids']),
      );
}

class AnalysisContent {
  final String overview;
  final List<String> overviewArticleIds;
  final String agreement;
  final String disagreement;
  final String uncertainty;
  final bool perspectivesSupported;
  final String perspectivesNote;
  final List<Perspective> perspectives;

  AnalysisContent({
    required this.overview,
    required this.overviewArticleIds,
    required this.agreement,
    required this.disagreement,
    required this.uncertainty,
    required this.perspectivesSupported,
    required this.perspectivesNote,
    required this.perspectives,
  });

  factory AnalysisContent.fromJson(Map<String, dynamic> j) => AnalysisContent(
        overview: _s(j['overview']),
        overviewArticleIds: _strings(j['overview_article_ids']),
        agreement: _s(j['agreement']),
        disagreement: _s(j['disagreement']),
        uncertainty: _s(j['uncertainty']),
        perspectivesSupported: j['perspectives_supported'] == true,
        perspectivesNote: _s(j['perspectives_note']),
        perspectives: _list(j['perspectives'], Perspective.fromJson),
      );

  Set<String> get citedArticleIds => {
        ...overviewArticleIds,
        for (final p in perspectives) ...p.articleIds,
      };
}

class AiSummary {
  /// ready | outdated | pending | failed | not_generated
  final String status;
  final String statusMessage;
  final String label;
  final DateTime? generatedAt;
  final String? model;
  final int version;
  final String inputScopeNote;
  final List<String> inputArticleIds;
  final AnalysisContent? content;

  AiSummary({
    required this.status,
    required this.statusMessage,
    required this.label,
    this.generatedAt,
    this.model,
    required this.version,
    required this.inputScopeNote,
    required this.inputArticleIds,
    this.content,
  });

  bool get hasContent => content != null;

  factory AiSummary.fromJson(Map<String, dynamic> j) => AiSummary(
        status: _s(j['status']),
        statusMessage: _s(j['status_message']),
        label: j['label'] == null ? 'AI-generated' : _s(j['label']),
        generatedAt: _date(j['generated_at']),
        model: j['model']?.toString(),
        version: (j['version'] as num?)?.toInt() ?? 0,
        inputScopeNote: _s(j['input_scope_note']),
        inputArticleIds: _strings(j['input_article_ids']),
        content: j['content'] is Map
            ? AnalysisContent.fromJson(Map<String, dynamic>.from(j['content']))
            : null,
      );

  static AiSummary unavailable(String message) => AiSummary(
        status: 'pending',
        statusMessage: message,
        label: 'AI-generated',
        version: 0,
        inputScopeNote: '',
        inputArticleIds: const [],
      );
}

class PublisherGroup {
  final String name;
  final List<Article> articles;
  PublisherGroup(this.name, this.articles);
}

class StoryDetail {
  final String id;
  final String headline;
  final DateTime? updatedAt;
  final List<Article> articles;
  final List<BackgroundResource> background;
  final String backgroundMessage;
  final AiSummary summary;
  final DateTime? lastSuccessfulCollectionAt;

  StoryDetail({
    required this.id,
    required this.headline,
    this.updatedAt,
    required this.articles,
    required this.background,
    required this.backgroundMessage,
    required this.summary,
    this.lastSuccessfulCollectionAt,
  });

  factory StoryDetail.fromJson(Map<String, dynamic> j) => StoryDetail(
        id: _s(j['id']),
        headline: _s(j['headline']),
        updatedAt: _date(j['updated_at']),
        articles: _list(j['articles'], Article.fromJson),
        background: _list(j['background'], BackgroundResource.fromJson),
        backgroundMessage: _s(j['background_message']).isEmpty
            ? 'No background resource available'
            : _s(j['background_message']),
        summary: j['summary'] is Map
            ? AiSummary.fromJson(Map<String, dynamic>.from(j['summary']))
            : AiSummary.unavailable('AI analysis is not available.'),
        lastSuccessfulCollectionAt: _date(j['last_successful_collection_at']),
      );

  DateTime get latestPublishedAt => articles
      .map((a) => a.publishedAt)
      .fold(DateTime.utc(1970), (a, b) => a.isAfter(b) ? a : b);

  /// One group per publisher that actually covered this story, newest first.
  List<PublisherGroup> get publishers {
    final map = <String, List<Article>>{};
    for (final a in articles) {
      map.putIfAbsent(a.publisher, () => []).add(a);
    }
    final names = map.keys.toList()..sort();
    return [
      for (final n in names)
        PublisherGroup(n, map[n]!..sort((a, b) => b.publishedAt.compareTo(a.publishedAt))),
    ];
  }

  Article? articleById(String id) {
    for (final a in articles) {
      if (a.id == id) return a;
    }
    return null;
  }

  /// Offline copy with expired articles removed. If the AI text cites an
  /// article that is gone, the text is withheld (same rule as the server).
  StoryDetail? withoutExpired(DateTime cutoff) {
    final kept = articles.where((a) => !a.publishedAt.isBefore(cutoff)).toList();
    if (kept.isEmpty) return null;
    if (kept.length == articles.length) return this;
    final keptIds = kept.map((a) => a.id).toSet();
    var summary = this.summary;
    final cited = {...summary.inputArticleIds, ...?summary.content?.citedArticleIds};
    if (summary.hasContent && !keptIds.containsAll(cited)) {
      summary = AiSummary.unavailable(
        'Some articles behind this analysis have expired. Connect to the internet to load the updated analysis.',
      );
    }
    return StoryDetail(
      id: id,
      headline: headline,
      updatedAt: updatedAt,
      articles: kept,
      background: background,
      backgroundMessage: backgroundMessage,
      summary: summary,
      lastSuccessfulCollectionAt: lastSuccessfulCollectionAt,
    );
  }
}
