/// Build-time configuration.
///
/// The app only talks to OUR server. It never fetches RSS feeds, never groups
/// stories and never calls an AI model; those all happen in the backend worker.
///
/// Override the server at build time:
///   flutter build apk --release --dart-define=API_BASE_URL=https://your-api.example.com
class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://mynews-api-mq6m.onrender.com',
  );

  /// Same rolling window as the server. Used to hide expired news from the
  /// offline cache even when the phone cannot reach the server.
  static const Duration retention = Duration(hours: 168);

  // Generous: a free-tier server can take up to a minute to wake from sleep.
  static const Duration requestTimeout = Duration(seconds: 60);

  static const String appVersion = '1.0.0';

  static const String feedbackEmail = String.fromEnvironment(
    'FEEDBACK_EMAIL',
    defaultValue: '',
  );
}
