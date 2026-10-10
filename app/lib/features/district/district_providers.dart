import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';

double _d(Object? v) => v is num ? v.toDouble() : 0;
int _i(Object? v) => v is num ? v.toInt() : 0;

/// Opis jednego budynku dzielnicy (scalone dane state + catalog).
class Building {
  Building({required this.id, required this.name, required this.icon, required this.level, required this.max, this.nextCost});
  final String id, name, icon;
  final int level, max;
  final int? nextCost; // null = poziom maksymalny
  bool get maxed => level >= max;
  bool get built => level > 0;
}

/// M5: trwająca budowa/rozbudowa (backend: state.construction). Jedna naraz.
class Construction {
  Construction({required this.building, required this.target, required this.startedAt, required this.endsAt, this.clockOffsetMs = 0});
  final String building;
  final int target, startedAt, endsAt; // ms epoch
  final int clockOffsetMs; // czas serwera minus czas lokalny w chwili odpowiedzi
  int get nowMs => DateTime.now().millisecondsSinceEpoch + clockOffsetMs;
  Duration left([int? nowMs]) => Duration(milliseconds: (endsAt - (nowMs ?? this.nowMs)).clamp(0, 30 * 86400000));
  double progress([int? nowMs]) {
    final total = endsAt - startedAt;
    if (total <= 0) return 1;
    return (((nowMs ?? this.nowMs) - startedAt) / total).clamp(0.0, 1.0);
  }

  bool get done => left() == Duration.zero;
}

/// „12 min”, „1 h 05 min”, „45 s”.
String fmtLeft(Duration d) {
  final s = d.inSeconds;
  if (s < 60) return '$s s';
  final m = (s / 60).ceil();
  if (m < 60) return '$m min';
  return '${m ~/ 60} h ${(m % 60).toString().padLeft(2, '0')} min';
}

/// Skarbiec idle budynku (Kawiarnia 24 h, Klub Nocny 72 h).
class Vault {
  Vault({required this.amount, required this.ratePerHour, required this.hours});
  final double amount, ratePerHour; // $/h w czasie świata (z mnożnikiem prędkości)
  final int hours;
  double get capacity => ratePerHour * hours;
  double get fill => capacity <= 0 ? 0 : (amount / capacity).clamp(0, 1);
  /// Godziny (realne) do zapełnienia.
  double get hoursToFull => ratePerHour <= 0 ? 0 : ((capacity - amount) / ratePerHour).clamp(0, hours.toDouble());
}

/// Dane ekranu Dzielnica — wszystko z jednego GET /state.
class DistrictData {
  DistrictData(this.raw, [this.npcs = const {}])
      : receivedAtMs = DateTime.now().millisecondsSinceEpoch;
  final int receivedAtMs;
  final Map<String, dynamic> raw;
  final Map<String, dynamic> npcs; // GET /npcs (pojemność Rezydencji); pusty, gdy niedostępny

  int get npcCount => _i(npcs['count']);
  int get npcSlots => _i(npcs['slots']);
  bool get vip => _i(state['vipUntil']) > DateTime.now().millisecondsSinceEpoch;

  Map<String, dynamic> get state => (raw['state'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> get catalog => (raw['catalog'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> get character => (raw['character'] as Map?)?.cast<String, dynamic>() ?? const {};
  double get speed => _d((raw['world'] as Map?)?['speed']).clamp(1, 1e9);
  double get cash => _d(state['cash']);
  int get buffet => _i(state['buffet']).clamp(0, 3);
  int get hallCost => _i(catalog['hallCost']);
  Map get _levels => (state['buildings'] as Map?) ?? const {};

  static const order = ['residence', 'garage', 'cafe', 'nightclub', 'club', 'hall'];
  static const hallRequires = ['residence', 'garage', 'cafe', 'nightclub', 'club'];

  List<Building> get buildings {
    final meta = (catalog['buildings'] as Map?) ?? const {};
    final maxes = (catalog['buildingMaxes'] as Map?) ?? const {};
    final costs = (catalog['buildingCostsBy'] as Map?) ?? const {};
    return [
      for (final id in order)
        () {
          final lv = _i(_levels[id]);
          final mx = _i(maxes[id]) == 0 ? 1 : _i(maxes[id]);
          final list = (costs[id] as List?) ?? const [];
          final cost = id == 'hall' ? (lv >= 1 ? null : hallCost) : (lv < mx && lv < list.length ? _i(list[lv]) : null);
          final m = (meta[id] as Map?) ?? const {};
          return Building(id: id, name: '${m['name'] ?? id}', icon: '${m['icon'] ?? '🏢'}', level: lv, max: mx, nextCost: cost);
        }(),
    ];
  }

  Building byId(String id) => buildings.firstWhere((b) => b.id == id);

  /// M5: trwająca budowa (null = brak).
  Construction? get construction {
    final c = state['construction'];
    if (c is! Map || !order.contains(c['building']) || _i(c['endsAt']) <= 0) return null;
    return Construction(building: c['building'] as String, target: _i(c['target']), startedAt: _i(c['startedAt']), endsAt: _i(c['endsAt']), clockOffsetMs: raw['serverTime'] is num ? _i(raw['serverTime']) - receivedAtMs : 0);
  }

  Vault? vault(String id) {
    final cfg = ((catalog['buildingVaults'] as Map?) ?? const {})[id] as Map?;
    final lv = _i(_levels[id]);
    if (cfg == null || lv < 1) return null;
    final rates = (cfg['rates'] as List?) ?? const [];
    final rate = lv <= rates.length ? _d(rates[lv - 1]) : 0.0;
    return Vault(amount: _d(((state['vaults'] as Map?) ?? const {})[id]), ratePerHour: rate * speed, hours: _i(cfg['hours']));
  }

  /// Sala Chwały: które budynki jeszcze nie są na maksimum.
  List<Building> get hallMissing => [for (final b in buildings) if (hallRequires.contains(b.id) && !b.maxed) b];
  bool get hallOpen => byId('hall').level >= 1;

  /// Auta w garażu: (id, zużycie 0–100).
  List<(String, double)> get cars {
    final c = (state['cars'] as Map?) ?? const {};
    return [for (final v in (state['garage'] as List?) ?? const []) ('$v', _d((c[v] as Map?)?['wear']))];
  }

  /// Flota: pełne dane aut (paliwo, zużycie, cennik z katalogu GARAGE).
  List<FleetCar> get fleet {
    final c = (state['cars'] as Map?) ?? const {};
    final g = ((catalog['vehicles'] as List?) ?? const []).whereType<Map>();
    final active = (state['vehicle'] as Map?)?['id'];
    return [
      for (final v in (state['garage'] as List?) ?? const [])
        () {
          final m = g.where((x) => x['id'] == v).firstOrNull ?? const {};
          final e = (c[v] as Map?) ?? const {};
          return FleetCar(
            id: '$v',
            name: '${m['name'] ?? v}',
            icon: const {'dostawczak': '🚚', 'sedan': '🚗', 'van': '🚐', 'furgonetka': '🚛', 'suv': '🚙', 'mistrz': '🏎️'}['$v'] ?? '🚗',
            fuel: e['fuel'] is num ? (e['fuel'] as num).toDouble() : 100,
            wear: _d(e['wear']),
            fuelPrice: m['fuelPrice'] is num ? (m['fuelPrice'] as num).toDouble() : 1,
            fuelPerHop: _i(m['fuel']),
            service: _i(m['service']),
            active: active == v,
          );
        }(),
    ];
  }

  String carName(String id) {
    final g = (catalog['vehicles'] as List?) ?? const [];
    final m = g.whereType<Map>().where((x) => x['id'] == id).firstOrNull;
    return '${m?['name'] ?? id}';
  }

  // Statystyki do Sali Chwały
  int get xp => _i(state['xp']);
  int get resets => _i((state['prestige'] as Map?)?['resets']);
  int get prestigeBonus => _i((state['prestige'] as Map?)?['bonus']);
  int get collected => _i((state['completed'] as Map?)?['collected']);
  List<String> get titles => [for (final t in (raw['titles'] as List?) ?? const []) if (t is Map) '${t['label']}'];
}

/// Auto we flocie gracza.
class FleetCar {
  FleetCar({required this.id, required this.name, required this.icon, required this.fuel, required this.wear,
      required this.fuelPrice, required this.fuelPerHop, required this.service, required this.active});
  final String id, name, icon;
  final double fuel, wear, fuelPrice; // fuel/wear 0–100 %
  final int fuelPerHop, service; // % paliwa na przystanek, koszt serwisu $
  final bool active; // auto wybrane do jazdy gracza
  int refuelCost(bool vip) => ((100 - fuel) * fuelPrice * (vip ? 0.8 : 1)).ceil();
}

/// Stan Dzielnicy: GET /state (budynki, skarbce, flota) + GET /npcs (pojemność Rezydencji), równolegle.
final districtProvider = FutureProvider.autoDispose<DistrictData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final r = await Future.wait([
    api.get('/api/worlds/$wid/state'),
    api.get('/api/worlds/$wid/npcs').catchError((_) => <String, dynamic>{}),
  ]);
  return DistrictData(r[0], r[1]);
});

class DistrictResult {
  const DistrictResult(this.message, {this.ok = true, this.data});
  final String message;
  final bool ok;
  final Map<String, dynamic>? data;
}

/// Akcje dzielnicy: POST /actions (rozbudowa, skarbce, Buffet) i POST /server_reset (Sala Chwały).
class DistrictActions {
  DistrictActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<DistrictResult> _run(String path, Map<String, dynamic> body, {bool refresh = true}) async {
    try {
      final r = await _api.post('$_base$path', body);
      return DistrictResult('${r['message'] ?? 'OK'}', data: r);
    } on ApiException catch (e) {
      return DistrictResult(e.message, ok: false);
    } finally {
      if (refresh) {
        _ref.invalidate(districtProvider);
        _ref.invalidate(dashboardProvider);
      }
    }
  }

  Future<DistrictResult> upgrade(String building) => _run('/actions', {'action': 'upgrade_building', 'building': building});
  Future<DistrictResult> collectCafe() => _run('/actions', {'action': 'collect', 'business': 'cafe'});
  Future<DistrictResult> collectNightclub() => _run('/actions', {'action': 'collect_nightclub'});
  /// Prawy panel: jeden klik odbiera skarbce Kawiarni i Klubu Nocnego (puste skarbce pomijane bez błędu).
  Future<DistrictResult> collectAll() async {
    var total = 0.0;
    final msgs = <String>[];
    for (final body in [
      {'action': 'collect', 'business': 'cafe'},
      {'action': 'collect_nightclub'},
    ]) {
      final r = await _run('/actions', body, refresh: false);
      if (r.ok) {
        final g = (r.data?['gained'] ?? r.data?['amount']);
        if (g is num) total += g;
        msgs.add(r.message);
      }
    }
    _ref.invalidate(districtProvider);
    _ref.invalidate(dashboardProvider);
    if (msgs.isEmpty) return const DistrictResult('Skarbce są puste — wróć później.', ok: false);
    return DistrictResult(total > 0 ? 'Odebrano ${total.round()} \$ ze skarbców.' : msgs.join(' · '));
  }
  Future<DistrictResult> upgradeBuffet() => _run('/actions', {'action': 'upgrade_buffet'});

  /// Karmienie masowe: wszyscy NPC dostają wybrany posiłek (1 Zwykły / 2 Dobry / 3 Premium).
  Future<DistrictResult> feedAll(int meal) => _run('/npcs/batch', {'action': 'all_to_buffet', 'npcs': 'all', 'meal': meal});

  // Garaż / flota
  Future<DistrictResult> refuel(String car) => _run('/actions', {'action': 'refuel', 'vehicle': car});
  Future<DistrictResult> service(String car) => _run('/actions', {'action': 'service_vehicle', 'vehicle': car});
  /// Salon aut: POST /actions buy_vehicle (cena, poziom i miejsce parkingowe sprawdza backend).
  Future<DistrictResult> buyVehicle(String id) => _run('/actions', {'action': 'buy_vehicle', 'vehicle': id});
  Future<DistrictResult> autoMechanic() => _run('/actions', {'action': 'auto_mechanic'});
  Future<DistrictResult> equip(String car) => _run('/actions', {'action': 'equip_vehicle', 'vehicle': car});

  /// Reset krok 1: podsumowanie + uzbrojenie licznika 10 s (serwer).
  Future<DistrictResult> resetArm() => _run('/server_reset', {}, refresh: false);
  /// Reset krok 3: wykonanie z tekstem potwierdzenia.
  Future<DistrictResult> resetExecute(String text) => _run('/server_reset', {'confirm_text': text});
}

final districtActionsProvider = Provider<DistrictActions>((ref) => DistrictActions(ref));
