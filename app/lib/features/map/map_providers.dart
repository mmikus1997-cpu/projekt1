import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../district/district_providers.dart';
import '../world/world_providers.dart';
import 'map_layout.dart';
export 'map_layout.dart' show MapDistrict, MapLayout, MapServiceSlot;

double _d(Object? v) => v is num ? v.toDouble() : 0;
int _i(Object? v) => v is num ? v.toInt() : 0;

/// Dzielnice zawsze dostępne (travel.ALWAYS_OPEN), niezależnie od Ery świata.
const alwaysOpen = {2, 7, 8};

/// Lokacja usługowa z dynamicznym popytem (GET /services).
class MapService {
  MapService(this.j);
  final Map<String, dynamic> j;
  String get id => '${j['id']}';
  String get name => '${j['name']}';
  String get icon => '${j['icon'] ?? '📍'}';
  int get district => _i(j['d']);
  double get demand => _d(j['demand']) == 0 ? 1 : _d(j['demand']);
  int get demandPct => (demand * 100).round();
  double get rateNow => _d(j['rateNow']);
  bool get unlocked => j['unlocked'] == true;
  int get level => _i(j['level']);
  /// Popyt w następnym oknie 6 h (GET /services: demandNext).
  int get demandNextPct => ((_d(j['demandNext']) == 0 ? demand : _d(j['demandNext'])) * 100).round();
  num get unlockCost => _i(j['unlock']);
  bool get canUnlock => j['canUnlock'] == true;
  int get levelReq => _i(j['level']);
}

/// Dane mapy: stan postaci (lokalizacja, podróż, era, flota) + usługi z popytem + porady asystenta.
class MapData {
  MapData({required this.layout, required this.district, required this.services, required this.demandTop, required this.tips, required this.changesAt});
  final MapLayout layout; // topografia z map_data.json
  final DistrictData district; // ponownie używamy modelu Dzielnicy (flota, gotówka, prędkość świata)
  final List<MapService> services;
  final List<Map<String, dynamic>> demandTop;
  final List<String> tips;
  final int changesAt;

  Map<String, dynamic> get _travelInfo => (district.raw['travelInfo'] as Map?)?.cast<String, dynamic>() ?? const {};
  int get here => _i(_travelInfo['district']) == 0 ? 1 : _i(_travelInfo['district']);
  Map<String, dynamic>? get travel => (_travelInfo['travel'] as Map?)?.cast<String, dynamic>();
  int get eraDistricts => _i((district.raw['era'] as Map?)?['districts']) == 0 ? 8 : _i((district.raw['era'] as Map?)?['districts']);
  bool isOpen(int id) => alwaysOpen.contains(id) || id <= eraDistricts;
  double get speed => district.speed;
  int get clockOffsetMs => district.raw['serverTime'] is num ? _i(district.raw['serverTime']) - district.receivedAtMs : 0;
  int get nowMs => DateTime.now().millisecondsSinceEpoch + clockOffsetMs;
  List<MapService> servicesIn(int d) => services.where((s) => s.district == d).toList();
  MapService? service(String id) => services.where((s) => s.id == id).firstOrNull;
  /// Czas serwera (ms) — podstawa cyklu dzień/noc.
  int get serverTime => _i(district.raw['serverTime']) == 0 ? DateTime.now().millisecondsSinceEpoch : _i(district.raw['serverTime']);
}

final mapProvider = FutureProvider.autoDispose<MapData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final base = '/api/worlds/$wid';
  final r = await Future.wait([
    api.get('$base/state'),
    api.get('$base/services'),
    api.get('$base/assistant').catchError((_) => <String, dynamic>{}),
  ]);
  final sv = r[1];
  final layout = await ref.watch(mapLayoutProvider.future);
  final tips = <String>[];
  for (final t in (r[2]['alerts'] as List?) ?? const []) {
    if (t is Map && t['text'] != null) tips.add('${t['text']}');
    if (t is String) tips.add(t);
  }
  return MapData(
    layout: layout,
    district: DistrictData(r[0]),
    services: [for (final m in (sv['services'] as List?) ?? const []) if (m is Map) MapService(m.cast())],
    demandTop: [for (final m in (sv['demandTop'] as List?) ?? const []) if (m is Map) m.cast<String, dynamic>()],
    tips: tips,
    changesAt: _i(sv['demandChangesAt']),
  );
});

class MapResult {
  const MapResult(this.message, {this.ok = true});
  final String message;
  final bool ok;
}

/// Akcje mapy: POST /travel (start), /travel/arrive (przyjazd).
class MapActions {
  MapActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<MapResult> _run(String path, Map<String, dynamic> body, String Function(Map<String, dynamic>) ok) async {
    try {
      return MapResult(ok(await _api.post('$_base$path', body)));
    } on ApiException catch (e) {
      return MapResult(e.message, ok: false);
    } finally {
      _ref.invalidate(mapProvider);
      _ref.invalidate(districtProvider);
      _ref.invalidate(dashboardProvider);
    }
  }

  Future<MapResult> travel(int target, String mode) => _run('/travel', {'target_district': target, 'mode': mode},
      (r) => '${switch (mode) { 'bus' => '🚌', 'car' => '🚗', _ => '👍' }} W drodze do ${(r['travel'] as Map?)?['toName'] ?? 'celu'}!');

  /// Odblokowanie lokacji usługowej (istniejący POST /services/{sid}/unlock).
  Future<MapResult> unlock(String sid) => _run('/services/$sid/unlock', {}, (r) => '🔓 Lokacja odblokowana!');

  Future<MapResult> arrive() => _run('/travel/arrive', {}, (r) => '📍 Jesteś w: ${r['districtName']}');
}

final mapActionsProvider = Provider<MapActions>((ref) => MapActions(ref));
