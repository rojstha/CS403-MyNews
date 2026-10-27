import 'package:flutter/material.dart';

import 'data/repository.dart';
import 'ui/story_list_screen.dart';

void main() {
  runApp(MyNewsApp(repository: NewsRepository()));
}

class MyNewsApp extends StatelessWidget {
  const MyNewsApp({super.key, required this.repository});
  final NewsRepository repository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'My News',
      debugShowCheckedModeBanner: false,
      theme: _theme(Brightness.light),
      darkTheme: _theme(Brightness.dark),
      home: StoryListScreen(repository: repository),
    );
  }

  ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF1F4E79),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: brightness == Brightness.light ? const Color(0xFFF3F6FA) : scheme.surface,
      appBarTheme: AppBarTheme(
        centerTitle: false,
        backgroundColor: brightness == Brightness.light ? const Color(0xFFF3F6FA) : scheme.surface,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: scheme.primary,
          letterSpacing: -0.3,
        ),
      ),
      chipTheme: const ChipThemeData(showCheckmark: false),
      pageTransitionsTheme: const PageTransitionsTheme(builders: {
        TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
      }),
    );
  }
}
