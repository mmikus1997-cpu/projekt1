import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';
import 'crew_models.dart';

/// Długość zmiany, dla której asystent liczy porady (wybierana w widgecie porad).
final crewTipHoursProvider = StateProvider<int>((ref) => 8);

/// Stan ekranu Ekipa: GET /npcs (rozliczenie całej ekipy) + /services (popyt) + /state (auta, gotówka) + /assistant.
/// Zapytania równolegle; porady asystenta są opcjonalne (błąd asystenta nie blokuje ekranu).
final crewProvider = FutureProvider.autoDispose<CrewData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final hours = ref.watch(crewTipHoursProvider);
  final base = '/api/worlds/$wid';
  // /npcs najpierw: rozlicza ekipę (wypłaty trafiają na konto), dopiero potem stan i porady są aktualne
  final npcs = await api.get('$base/npcs');
  final rest = await Future.wait([
    api.get('$base/services'),
    api.get('$base/state'),
    api.get('$base/assistant?hours=$hours').then<Map<String, dynamic>?>((v) => v).catchError((_) => null),
  ]);
  final services = ((rest[0]!['services'] as List?) ?? const []).whereType<Map>().map((m) => ServiceInfo(m.cast())).toList();
  final state = (rest[1]!['state'] as Map?)?.cast<String, dynamic>() ?? const {};
  return CrewData(npcsJson: npcs, services: services, state: state, assistant: rest[2]);
});

/// Wynik akcji do pokazania w snackbarze.
class CrewResult {
  const CrewResult(this.message, {this.ok = true});
  final String message;
  final bool ok;
}

/// Akcje ekranu Ekipa. Każda kończy się odświeżeniem ekipy i HUD (gotówka).
class CrewActions {
  CrewActions(this._ref);
  final Ref _ref;

  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<CrewResult> _run(Future<Map<String, dynamic>> Function() call) async {
    try {
      final r = await call();
      return CrewResult('${r['message'] ?? 'OK'}');
    } on ApiException catch (e) {
      return CrewResult(e.message, ok: false);
    } finally {
      _ref.invalidate(crewProvider);
      _ref.invalidate(dashboardProvider);
    }
  }

  Future<CrewResult> dispatch(int npc, String service, int hours, {String? car}) => _run(() => _api.post(
      '$_base/npcs/$npc/dispatch', {'service_id': service, 'hours': hours, 'car_id': car}));

  Future<CrewResult> taxi(int npc, int hours, {String? car}) =>
      _run(() => _api.post('$_base/npcs/$npc/taxi', {'hours': hours, 'car_id': car}));

  Future<CrewResult> recall(int npc) => _run(() => _api.post('$_base/npcs/$npc/recall'));

  Future<CrewResult> feed(int npc) => _run(() => _api.post('$_base/npcs/feed', {'npc_id': npc}));

  Future<CrewResult> setRole(int npc, String role) => _run(() => _api.post('$_base/npcs/$npc/role', {'role': role}));

  Future<CrewResult> recruit(String role) => _run(() => _api.post('$_base/npcs/recruit', {'role': role}));

  /// Akcja zbiorcza POST /npcs/batch. Wynik: komunikat zbiorczy + liczba udanych.
  Future<CrewResult> batch(Map<String, dynamic> body) => _run(() => _api.post('$_base/npcs/batch', body));

  /// „Odbierz wszystkich”: wypłaty ze zmian i Taxi trafiają na konto automatycznie przy rozliczeniu ekipy —
  /// tu wymuszamy rozliczenie (GET /npcs) i pokazujemy przyrost gotówki.
  Future<CrewResult> collect() async {
    try {
      final before = ((await _api.get('$_base/state'))['state'] as Map?)?['cash'] as num? ?? 0;
      await _api.get('$_base/npcs');
      final after = ((await _api.get('$_base/state'))['state'] as Map?)?['cash'] as num? ?? 0;
      final d = (after - before).round();
      return CrewResult(d > 0 ? 'Odebrano wypłaty ekipy: +$d \$' : 'Brak nowych wypłat — zakończone zmiany są już na koncie.');
    } on ApiException catch (e) {
      return CrewResult(e.message, ok: false);
    } finally {
      _ref.invalidate(crewProvider);
      _ref.invalidate(dashboardProvider);
    }
  }
}

final crewActionsProvider = Provider<CrewActions>((ref) => CrewActions(ref));
