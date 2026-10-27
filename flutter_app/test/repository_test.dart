import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:my_news/data/repository.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fixtures.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  NewsRepository repo(MockClient c, {DateTime? at}) =>
      NewsRepository(client: c, baseUrl: 'https://api.example', clock: () => at ?? now);

  test('only calls the My News server, never feeds or AI services', () async {
    final urls = <Uri>[];
    final c = MockClient((req) async {
      urls.add(req.url);
      return http.Response(req.url.path == '/stories' ? body(storyListJson()) : body(storyDetailJson()), 200);
    });
    final r = repo(c);
    await r.fetchStories();
    await r.fetchStory('s-new');
    expect(urls.map((u) => '${u.host}${u.path}'), ['api.example/stories', 'api.example/stories/s-new']);
  });

  test('live list is sorted newest first', () async {
    final r = repo(MockClient((_) async => http.Response(body(storyListJson()), 200)));
    final loaded = await r.fetchStories();
    expect(loaded.fromCache, isFalse);
    expect(loaded.data.stories.map((s) => s.id), ['s-new', 's-old']);
  });

  test('offline: serves cache, labels it, and hides expired articles', () async {
    await repo(MockClient((_) async => http.Response(body(storyListJson()), 200))).fetchStories();

    // Ten hours later, with no network: the 160 h story is now 170 h old.
    final offline = repo(MockClient((_) async => throw const SocketException('down')),
        at: now.add(const Duration(hours: 10)));
    final loaded = await offline.fetchStories();
    expect(loaded.fromCache, isTrue);
    expect(loaded.offlineReason, contains('No internet'));
    expect(loaded.data.stories.map((s) => s.id), ['s-new']);
    // NPR's 165 h article in s-new has expired too, so only BBC remains.
    expect(loaded.data.stories.single.publishers, ['BBC News']);
  });

  test('offline detail drops expired sources and withholds AI text that cited them', () async {
    await repo(MockClient((_) async => http.Response(body(storyDetailJson()), 200))).fetchStory('s-new');
    final offline = repo(MockClient((_) async => throw const SocketException('down')),
        at: now.add(const Duration(hours: 5)));
    final loaded = await offline.fetchStory('s-new');
    expect(loaded.fromCache, isTrue);
    expect(loaded.data.publishers.map((p) => p.name), ['BBC News']);
    expect(loaded.data.summary.content, isNull);
    expect(loaded.data.summary.statusMessage, contains('expired'));
  });

  test('no cache and no network gives a readable error', () async {
    final r = repo(MockClient((_) async => throw const SocketException('down')));
    expect(r.fetchStories(), throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('internet'))));
  });

  test('server errors become friendly messages, not raw output', () async {
    final r = repo(MockClient((_) async => http.Response('<html>Bad gateway</html>', 502)));
    expect(r.fetchStories(), throwsA(isA<ApiException>().having((e) => e.message, 'message', contains('502'))));
  });

  test('404 is not replaced by a stale cached copy', () async {
    await repo(MockClient((_) async => http.Response(body(storyDetailJson()), 200))).fetchStory('s-new');
    final r = repo(MockClient((_) async => http.Response('{"detail":"Story not found or expired"}', 404)));
    expect(r.fetchStory('s-new'), throwsA(isA<ApiException>().having((e) => e.notFound, 'notFound', isTrue)));
  });
}
