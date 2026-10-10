import 'dart:async';

import 'package:battery_plus/battery_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// UI v2 Etap 5: Tryb Eco („Zoptymalizuj wydajność”) — zapisywany lokalnie (shared_preferences).
/// Włączony wyłącza: płynny dzień/noc, animacje aut NPC (zostaje linia trasy), dym, łódkę, sarnę, pulsowanie i cienie.
class EcoModeController extends StateNotifier<bool> {
  EcoModeController() : super(false) {
    SharedPreferences.getInstance().then((p) {
      if (mounted) state = p.getBool(_key) ?? false;
    });
  }
  static const _key = 'app.eco';

  Future<void> set(bool v) async {
    state = v;
    (await SharedPreferences.getInstance()).setBool(_key, v);
  }
}

final ecoModeProvider = StateNotifierProvider<EcoModeController, bool>((_) => EcoModeController());

/// Systemowy tryb oszczędzania baterii (Android/iOS przez battery_plus). Na WWW/desktopie brak API → false.
/// Odpytywany co 30 s — zmiana w systemie zatrzymuje/wznawia animacje bez restartu aplikacji.
final batterySaverProvider = StreamProvider<bool>((ref) async* {
  if (kIsWeb || !(defaultTargetPlatform == TargetPlatform.android || defaultTargetPlatform == TargetPlatform.iOS)) {
    yield false;
    return;
  }
  final b = Battery();
  Future<bool> read() async {
    try {
      return await b.isInBatterySaveMode;
    } catch (_) {
      return false;
    }
  }

  yield await read();
  yield* Stream.periodic(const Duration(seconds: 30)).asyncMap((_) => read());
});

/// true = wolno odpalać ozdobne animacje (nie Eco i nie oszczędzanie baterii).
final effectsOnProvider = Provider<bool>((ref) => !ref.watch(ecoModeProvider) && !(ref.watch(batterySaverProvider).valueOrNull ?? false));
