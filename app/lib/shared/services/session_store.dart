import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Trwałe dane sesji: token, CSRF, język, wybrany świat.
/// Backend City Empire używa tokenu sesji (nie JWT) + tokenu CSRF dla żądań zmieniających stan.
class SessionStore {
  SessionStore(this._p);
  final SharedPreferences _p;

  String? get token => _p.getString('session.token');
  String? get csrf => _p.getString('session.csrf');
  String get language => _p.getString('app.language') ?? 'pl';
  int? get worldId => _p.getInt('session.world');

  Future<void> saveSession(String token, String csrf) async {
    await _p.setString('session.token', token);
    await _p.setString('session.csrf', csrf);
  }

  Future<void> saveCsrf(String csrf) => _p.setString('session.csrf', csrf);
  Future<void> saveLanguage(String lang) => _p.setString('app.language', lang);
  Future<void> saveWorld(int id) => _p.setInt('session.world', id);

  Future<void> clear() async {
    await _p.remove('session.token');
    await _p.remove('session.csrf');
    await _p.remove('session.world');
  }
}

/// Nadpisywany w main() po SharedPreferences.getInstance().
final sessionStoreProvider = Provider<SessionStore>((ref) => throw UnimplementedError());
