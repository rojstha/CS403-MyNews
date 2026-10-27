import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:my_news/data/repository.dart';
import 'package:my_news/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fixtures.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Future<void> pump(WidgetTester tester, MockClient client) async {
    await tester.binding.setSurfaceSize(const Size(412, 915)); // typical Android phone
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(MyNewsApp(repository: NewsRepository(client: client, baseUrl: 'https://api.example')));
    await tester.pumpAndSettle();
  }

  MockClient server({Map<String, dynamic>? detail, Map<String, dynamic>? list}) => MockClient((req) async {
        if (req.url.path == '/stories') return http.Response(body(list ?? storyListJson()), 200);
        return http.Response(body(detail ?? storyDetailJson()), 200);
      });

  testWidgets('story list shows headline, publisher count, server update time', (tester) async {
    await pump(tester, server());
    expect(find.text('Top stories'), findsOneWidget);
    expect(find.text('Two charged over RAF Fairford plot'), findsOneWidget);
    expect(find.text('2 publishers'), findsOneWidget);
    expect(find.text('1 publisher'), findsOneWidget);
    expect(find.textContaining('Server updated'), findsOneWidget);
  });

  testWidgets('error state with retry recovers', (tester) async {
    var fail = true;
    await pump(tester, MockClient((req) async {
      if (fail) throw const SocketException('down');
      return http.Response(body(storyListJson()), 200);
    }));
    expect(find.text('Can’t load stories'), findsOneWidget);
    fail = false;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();
    expect(find.text('Two charged over RAF Fairford plot'), findsOneWidget);
  });

  testWidgets('empty state', (tester) async {
    await pump(tester, server(list: storyListJson(stories: [])));
    expect(find.text('No stories yet'), findsOneWidget);
  });

  testWidgets('multi-source filter hides single-source stories', (tester) async {
    await pump(tester, server());
    await tester.tap(find.text('2+ sources'));
    await tester.pumpAndSettle();
    expect(find.text('Older story about a river project'), findsNothing);
    expect(find.text('Two charged over RAF Fairford plot'), findsOneWidget);
  });

  testWidgets('detail shows only covering publishers, background, AI entry; back works', (tester) async {
    await pump(tester, server());
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    expect(find.text('Original coverage'), findsOneWidget);
    expect(find.text('BBC News'), findsOneWidget);
    expect(find.text('NPR'), findsOneWidget);
    expect(find.text('Fox News'), findsNothing);
    await tester.scrollUntilVisible(find.text('RAF Fairford'), 200);
    expect(find.text('RAF Fairford'), findsOneWidget);
    expect(find.text('AI-generated'), findsOneWidget); // overview badge
    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();
    expect(find.text('Top stories'), findsOneWidget);
  });

  testWidgets('no background shows the required message', (tester) async {
    await pump(tester, server(detail: storyDetailJson(background: false)));
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('No background resource available'), 200);
    expect(find.text('No background resource available'), findsOneWidget);
  });

  testWidgets('AI analysis and perspective screens with citations', (tester) async {
    await pump(tester, server());
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Overview & perspectives'), 200);
    await tester.tap(find.text('Overview & perspectives'));
    await tester.pumpAndSettle();
    expect(find.text('Where sources agree'), findsOneWidget);
    expect(find.text('[1] NPR'), findsWidgets);
    await tester.scrollUntilVisible(find.text('Prosecutors'), 200);
    await tester.tap(find.text('Prosecutors'));
    await tester.pumpAndSettle();
    expect(find.text('Supported claims'), findsOneWidget);
    expect(find.text('Evidence and limits'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Defence'), 200);
    await tester.tap(find.text('Defence'));
    await tester.pumpAndSettle();
    expect(find.text('The men deny the charges.'), findsOneWidget);
  });

  testWidgets('insufficient evidence is stated, not invented', (tester) async {
    await pump(tester, server(detail: storyDetailJson(perspectives: false)));
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Overview & perspectives'), 200);
    await tester.tap(find.text('Overview & perspectives'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.textContaining('Insufficient evidence for distinct perspectives'), 200);
    expect(find.textContaining('Insufficient evidence for distinct perspectives'), findsOneWidget);
  });

  testWidgets('failed AI shows honest status and keeps original coverage', (tester) async {
    await pump(tester, server(detail: storyDetailJson(status: 'failed')));
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    expect(find.textContaining('currently unavailable'), findsOneWidget);
    expect(find.textContaining('original wording, not the full article'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Overview & perspectives'), 200);
    await tester.tap(find.text('Overview & perspectives'));
    await tester.pumpAndSettle();
    expect(find.text('Where sources agree'), findsNothing);
    expect(find.text('Back to original coverage'), findsOneWidget);
  });

  testWidgets('every screen lays out without overflow at 1.5x text size', (tester) async {
    tester.platformDispatcher.textScaleFactorTestValue = 1.5;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.binding.setSurfaceSize(const Size(360, 740)); // small Android phone
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(MyNewsApp(repository: NewsRepository(client: server(), baseUrl: 'https://api.example')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Two charged over RAF Fairford plot'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Overview & perspectives'), 200);
    await tester.tap(find.text('Overview & perspectives'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Prosecutors'), 200);
    await tester.tap(find.text('Prosecutors'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
