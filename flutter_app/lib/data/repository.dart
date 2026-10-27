import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../models.dart';

/// A readable error for the UI. Never shows raw exception text to readers.
class ApiException implements Exception {
  final String message;
  final bool notFound;
  ApiException(this.message, {this.notFound = false});
  @override
  String toString() => message;
}

/// Result of a load: live data, or cached data when the server is unreachable.
class Loaded<T> {
  final T data;
  final bool fromCache;
  final DateTime syncedAt;
  final String? offlineReason;
  Loaded(this.data, {required this.fromCache, required this.syncedAt, this.offlineReason});
}

/// Reads processed results from the My News server and keeps a local copy.
///
/// This is the ONLY network code that touches news data in the app. It calls
/// GET /stories and GET /stories/{id}; it never contacts publishers' feeds or
/// an AI service.
class NewsRepository {
  NewsRepository({http.Client? client, String? baseUrl, DateTime Function()? clock})
      : _client = client ?? http.Client(),
        _base = (baseUrl ?? AppConfig.apiBaseUrl).replaceAll(RegExp(r'/+$'), ''),
        _clock = clock ?? DateTime.now;

  final http.Client _client;
  final String _base;
  final DateTime Function() _clock;

  static const _listKey = 'cache.stories';
  static const _detailPrefix = 'cache.story.';

  DateTime get _cutoff => _clock().toUtc().subtract(AppConfig.retention);

  Future<Map<String, dynamic>> _getJson(String path) async {
    final uri = Uri.parse('$_base$path');
    http.Response res;
    try {
      res = await _client.get(uri, headers: {'Accept': 'application/json'}).timeout(AppConfig.requestTimeout);
    } on TimeoutException {
      throw ApiException('The server took too long to respond. It may be waking up; please try again.');
    } on SocketException {
      throw ApiException('No internet connection, or the My News server is unreachable.');
    } on http.ClientException {
      throw ApiException('Could not connect to the My News server.');
    }
    if (res.statusCode == 404) {
      throw ApiException('This story is no longer available. It may have expired.', notFound: true);
    }
    if (res.statusCode != 200) {
      throw ApiException('The My News server returned an error (${res.statusCode}). Please try again shortly.');
    }
    try {
      final body = jsonDecode(utf8.decode(res.bodyBytes));
      if (body is Map<String, dynamic>) return body;
    } catch (_) {}
    throw ApiException('The server sent a response the app could not read.');
  }

  Future<void> _save(String key, Map<String, dynamic> json) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, jsonEncode({'synced_at': _clock().toUtc().toIso8601String(), 'data': json}));
    } catch (_) {
      // Caching is best-effort; a failure must not break live reading.
    }
  }

  Future<(Map<String, dynamic>, DateTime)?> _load(String key) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(key);
      if (raw == null) return null;
      final j = jsonDecode(raw) as Map<String, dynamic>;
      return (Map<String, dynamic>.from(j['data'] as Map), DateTime.parse(j['synced_at'] as String));
    } catch (_) {
      return null;
    }
  }

  Future<Loaded<StoryList>> fetchStories() async {
    try {
      final json = await _getJson('/stories');
      await _save(_listKey, json);
      return Loaded(StoryList.fromJson(json), fromCache: false, syncedAt: _clock().toUtc());
    } on ApiException catch (e) {
      final cached = await _load(_listKey);
      if (cached == null) rethrow;
      final list = StoryList.fromJson(cached.$1).withoutExpired(_cutoff);
      return Loaded(list, fromCache: true, syncedAt: cached.$2, offlineReason: e.message);
    }
  }

  Future<Loaded<StoryDetail>> fetchStory(String id) async {
    try {
      final json = await _getJson('/stories/${Uri.encodeComponent(id)}');
      await _save('$_detailPrefix$id', json);
      return Loaded(StoryDetail.fromJson(json), fromCache: false, syncedAt: _clock().toUtc());
    } on ApiException catch (e) {
      if (e.notFound) rethrow; // the server says it is gone: do not show a stale copy
      final cached = await _load('$_detailPrefix$id');
      if (cached == null) rethrow;
      final detail = StoryDetail.fromJson(cached.$1).withoutExpired(_cutoff);
      if (detail == null) {
        throw ApiException('This story has expired and is no longer shown.', notFound: true);
      }
      return Loaded(detail, fromCache: true, syncedAt: cached.$2, offlineReason: e.message);
    }
  }

  /// Remove cached story details that have fully expired.
  Future<void> pruneCache() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      for (final key in prefs.getKeys().where((k) => k.startsWith(_detailPrefix))) {
        final cached = await _load(key);
        if (cached == null || StoryDetail.fromJson(cached.$1).withoutExpired(_cutoff) == null) {
          await prefs.remove(key);
        }
      }
    } catch (_) {}
  }
}
