import 'package:flutter/foundation.dart';

/// Adres backendu.
/// Web: ten sam origin, z którego załadowano aplikację (serwer podglądu proxuje /api → :3000),
/// dzięki temu działa zarówno lokalnie, jak i za proxy podglądu.
/// Mobile/desktop: `--dart-define=API_BASE=http://10.0.2.2:3000` (emulator Androida) itd.
class AppConfig {
  static const version = '0.1.0';
  static const _apiBase = String.fromEnvironment('API_BASE');

  static String get apiBase {
    if (_apiBase.isNotEmpty) return _apiBase;
    if (kIsWeb) return Uri.base.origin;
    return 'http://localhost:3000';
  }
}
