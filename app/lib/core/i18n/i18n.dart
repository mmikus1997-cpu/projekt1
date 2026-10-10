import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../shared/services/session_store.dart';
import '../network/api_client.dart';
import 'ui_strings.dart';

const supportedLanguages = ['pl', 'en', 'de', 'fr'];

/// Tłumaczenia: teksty interfejsu aplikacji (ui_strings.dart) + słownik gry z backendu
/// GET /api/i18n/{lang} (sety, sloty, kupony…), cache w shared_preferences (działa offline).
class Translations {
  const Translations(this.lang, this.remote);
  final String lang;
  final Map<String, String> remote;

  String t(String key, [Map<String, Object?> args = const {}]) {
    var s = uiStrings[lang]?[key] ?? remote[key] ?? uiStrings['pl']?[key] ?? key;
    args.forEach((k, v) => s = s.replaceAll('{$k}', '$v'));
    return s;
  }
}

class TranslationsController extends StateNotifier<Translations> {
  TranslationsController(this._ref) : super(Translations(_ref.read(sessionStoreProvider).language, const {})) {
    _load(state.lang);
  }
  final Ref _ref;

  Future<void> setLanguage(String lang) async {
    if (!supportedLanguages.contains(lang)) return;
    await _ref.read(sessionStoreProvider).saveLanguage(lang);
    state = Translations(lang, state.remote);
    await _load(lang);
  }

  Future<void> _load(String lang) async {
    final prefs = await SharedPreferences.getInstance();
    final cached = prefs.getString('i18n.$lang');
    if (cached != null) state = Translations(lang, Map<String, String>.from(jsonDecode(cached) as Map));
    try {
      final r = await _ref.read(apiClientProvider).get('/api/i18n/$lang');
      final strings = Map<String, String>.from((r['strings'] as Map).map((k, v) => MapEntry('$k', '$v')));
      await prefs.setString('i18n.$lang', jsonEncode(strings));
      if (state.lang == lang) state = Translations(lang, strings);
    } catch (_) {
      // offline: zostaje cache lub same teksty interfejsu
    }
  }
}

final translationsProvider =
    StateNotifierProvider<TranslationsController, Translations>((ref) => TranslationsController(ref));
