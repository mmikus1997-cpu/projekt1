import 'dart:math';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/services/session_store.dart';
import '../config.dart';

/// Błąd API z czytelnym komunikatem z backendu (pole `detail`, już przetłumaczone przez 8.5).
class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  bool get unauthorized => status == 401;
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this._store, {void Function()? onUnauthorized})
      : dio = Dio(BaseOptions(
          baseUrl: AppConfig.apiBase,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
          sendTimeout: const Duration(seconds: 20),
          contentType: Headers.jsonContentType,
        )) {
    dio.interceptors.add(AuthInterceptor(_store, onUnauthorized));
    dio.interceptors.add(LocaleInterceptor(_store));
  }

  final SessionStore _store;
  final Dio dio;

  Future<Map<String, dynamic>> get(String path) => _call(() => dio.get(path));

  /// POST zawsze z ciałem JSON (backend odrzuca puste ciało kodem 415).
  Future<Map<String, dynamic>> post(String path, [Map<String, dynamic>? body]) =>
      _call(() => dio.post(path, data: body ?? const {}));

  Future<Map<String, dynamic>> _call(Future<Response> Function() send) async {
    try {
      final r = await send();
      final data = r.data;
      return data is Map<String, dynamic> ? data : {'data': data};
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  static ApiException _toApiException(DioException e) {
    final r = e.response;
    if (r == null) return ApiException(0, 'Brak połączenia z serwerem.');
    final d = r.data;
    var msg = 'Błąd serwera (${r.statusCode}).';
    if (d is Map && d['detail'] != null) {
      final det = d['detail'];
      if (det is String) {
        msg = det;
      } else if (det is List && det.isNotEmpty && det.first is Map) {
        msg = (det.first as Map)['msg']?.toString() ?? msg; // 422 walidacji Pydantic
      }
    }
    return ApiException(r.statusCode ?? 0, msg);
  }
}

/// Dokłada token sesji, CSRF, klucz idempotencji dla POST; obsługuje 401.
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._store, this._onUnauthorized);
  final SessionStore _store;
  final void Function()? _onUnauthorized;
  final _rnd = Random.secure();

  String _key() => List.generate(16, (_) => _rnd.nextInt(256).toRadixString(16).padLeft(2, '0')).join();

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // Tryb deweloperski backendu zwraca token w JSON zamiast ciasteczka (działa też na mobile).
    options.headers['X-City-Preview-Session'] = '1';
    final token = _store.token;
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
      // proxy podglądu potrafi podmienić Authorization — backend czyta najpierw X-City-Session
      options.headers['X-City-Session'] = token;
    }
    final csrf = _store.csrf;
    if (csrf != null && options.method != 'GET') options.headers['X-CSRF-Token'] = csrf;
    if (options.method == 'POST') options.headers.putIfAbsent('Idempotency-Key', _key);
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final isAuthCall = err.requestOptions.path.startsWith('/api/auth/');
    if (err.response?.statusCode == 401 && !isAuthCall) _onUnauthorized?.call();
    handler.next(err);
  }
}

/// Accept-Language → backend tłumaczy komunikaty błędów (Etap 8.5).
class LocaleInterceptor extends Interceptor {
  LocaleInterceptor(this._store);
  final SessionStore _store;
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.headers['Accept-Language'] = _store.language;
    handler.next(options);
  }
}

/// Callback 401 ustawia AuthController (unika cyklu zależności providerów).
final unauthorizedHandlerProvider = StateProvider<void Function()?>((ref) => null);

final apiClientProvider = Provider<ApiClient>((ref) {
  final store = ref.watch(sessionStoreProvider);
  return ApiClient(store, onUnauthorized: () => ref.read(unauthorizedHandlerProvider)?.call());
});
