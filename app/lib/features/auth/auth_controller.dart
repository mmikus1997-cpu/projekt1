import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../shared/models/models.dart';
import '../../shared/services/session_store.dart';

enum AuthStatus { unknown, loggedOut, loggedIn }

class AuthState {
  const AuthState(this.status, {this.user, this.guardianPending = false});
  final AuthStatus status;
  final User? user;
  final bool guardianPending;
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref) : super(const AuthState(AuthStatus.unknown)) {
    _ref.read(unauthorizedHandlerProvider.notifier).state = _expire;
  }
  final Ref _ref;

  ApiClient get _api => _ref.read(apiClientProvider);
  SessionStore get _store => _ref.read(sessionStoreProvider);

  /// Splash: czy zapisany token jest wciąż ważny?
  Future<void> restore() async {
    if (_store.token == null) {
      state = const AuthState(AuthStatus.loggedOut);
      return;
    }
    try {
      final me = await _api.get('/api/me');
      if (me['csrf'] is String) await _store.saveCsrf(me['csrf'] as String);
      final gate = me['ageGate'] as Map?;
      state = AuthState(AuthStatus.loggedIn,
          user: User.fromJson((me['user'] as Map).cast()), guardianPending: gate?['guardianStatus'] == 'pending');
    } on ApiException catch (e) {
      if (e.unauthorized) await _store.clear();
      state = const AuthState(AuthStatus.loggedOut);
    }
  }

  Future<void> login(String username, String password) async {
    final r = await _api.post('/api/auth/login', {'username': username.trim(), 'password': password});
    await _accept(r);
  }

  /// Rejestracja z Age Gate (Etap 1.8): data urodzenia, <16 → e-mail opiekuna.
  Future<void> register({
    required String username,
    required String password,
    required String birthDate,
    required bool consent,
    String? guardianEmail,
  }) async {
    await _api.post('/api/auth/register', {
      'username': username.trim(),
      'password': password,
      'consent': consent,
      if (birthDate.trim().isNotEmpty) 'birth_date': birthDate.trim(),
      if (guardianEmail != null && guardianEmail.trim().isNotEmpty) 'guardian_email': guardianEmail.trim(),
    });
    await login(username, password);
  }

  Future<void> _accept(Map<String, dynamic> r) async {
    final token = r['previewSessionToken'];
    if (token is! String) {
      throw ApiException(500, 'Serwer nie jest w trybie deweloperskim (brak tokenu sesji).');
    }
    await _store.saveSession(token, '${r['csrf']}');
    // po zalogowaniu sprawdzamy sesję (/api/me) — błąd pokazujemy, zamiast po cichu wracać do formularza
    try {
      await _restoreStrict();
    } catch (e) {
      await _store.clear();
      state = const AuthState(AuthStatus.loggedOut);
      throw ApiException(0, 'Zalogowano, ale serwer nie potwierdził sesji: $e');
    }
  }

  Future<void> _restoreStrict() async {
    final me = await _api.get('/api/me');
    if (me['csrf'] is String) await _store.saveCsrf(me['csrf'] as String);
    final gate = me['ageGate'] as Map?;
    state = AuthState(AuthStatus.loggedIn,
        user: User.fromJson((me['user'] as Map).cast()), guardianPending: gate?['guardianStatus'] == 'pending');
  }

  Future<void> logout() async {
    try {
      await _api.post('/api/auth/logout');
    } catch (_) {}
    await _store.clear();
    state = const AuthState(AuthStatus.loggedOut);
  }

  void _expire() {
    if (state.status != AuthStatus.loggedIn) return;
    _store.clear();
    state = const AuthState(AuthStatus.loggedOut);
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((ref) => AuthController(ref));
