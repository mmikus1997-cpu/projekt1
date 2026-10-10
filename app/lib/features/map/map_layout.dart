import 'dart:convert';
import 'dart:ui';

import 'map_routes.dart';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// UI v2 Etap 2: topografia mapy z `assets/data/map_data.json` (żadnych współrzędnych w widgetach).
/// Gdy backend się otworzy, ten sam JSON może przyjść z API — model zostaje bez zmian.
double _d(Object? v) => v is num ? v.toDouble() : 0;
Offset _pt(Object? v) => v is List && v.length >= 2 ? Offset(_d(v[0]), _d(v[1])) : Offset.zero;
List<Offset> _pts(Object? v) => [for (final p in (v as List?) ?? const []) _pt(p)];
Color _hex(Object? v, Color fallback) {
  final s = '$v'.replaceFirst('#', '');
  final n = int.tryParse(s.length == 6 ? 'FF$s' : s, radix: 16);
  return n == null ? fallback : Color(n);
}

/// Dzielnica świata (id = travel.DISTRICTS). kind: city | resource | special.
class MapDistrict {
  const MapDistrict(this.id, this.name, this.icon, this.kind, this.region, this.x, this.y);
  final int id;
  final String name, icon, kind, region;
  final double x, y;
  Offset get pos => Offset(x, y);
}

class MapRegion {
  MapRegion(this.id, this.name, this.color, this.label, this.polygon, this.districts);
  final String id, name;
  final Color color;
  final Offset label;
  final List<Offset> polygon;
  final List<int> districts;
}

class MapRoad {
  MapRoad(this.a, this.b, this.kind, this.bridge);
  final int a, b;
  final String kind; // main | local
  final bool bridge;
}

class MapRiver {
  MapRiver(this.name, this.width, this.points);
  final String name;
  final double width;
  final List<Offset> points;
}

class MapOval {
  MapOval(this.name, this.center, this.rx, this.ry);
  final String name;
  final Offset center;
  final double rx, ry;
}

class MapLandmark {
  MapLandmark(this.id, this.name, this.icon, this.pos, this.note);
  final String id, name, icon, note;
  final Offset pos;
}

/// Pozycja lokacji usługowej (id = services.SERVICES) + opis do panelu.
class MapServiceSlot {
  MapServiceSlot(this.id, this.district, this.pos, this.desc);
  final String id, desc;
  final int district;
  final Offset pos;
}

class MapLayout {
  MapLayout(this.j)
      : homeDistrict = (j['home_district'] as num?)?.toInt() ?? 1,
        width = _d((j['board'] as Map?)?['width']),
        height = _d((j['board'] as Map?)?['height']),
        background = _hex((j['board'] as Map?)?['background'], const Color(0xFF0E1A2E)),
        sea = _pts((j['water'] as Map?)?['sea']),
        rivers = [
          for (final r in ((j['water'] as Map?)?['rivers'] as List?) ?? const [])
            if (r is Map) MapRiver('${r['name']}', _d(r['width']), _pts(r['points']))
        ],
        lakes = _ovals((j['water'] as Map?)?['lakes']),
        swamps = _ovals((j['water'] as Map?)?['swamps']),
        regions = [
          for (final r in (j['regions'] as List?) ?? const [])
            if (r is Map)
              MapRegion('${r['id']}', '${r['name']}', _hex(r['color'], const Color(0xFF1B2740)), _pt(r['label']), _pts(r['polygon']),
                  [for (final x in (r['districts'] as List?) ?? const []) (x as num).toInt()])
        ],
        districts = [
          for (final m in (j['districts'] as List?) ?? const [])
            if (m is Map)
              MapDistrict((m['id'] as num).toInt(), '${m['name']}', '${m['icon']}', '${m['kind']}', '${m['region']}', _d(m['x']), _d(m['y']))
        ],
        roads = [
          for (final r in (j['roads'] as List?) ?? const [])
            if (r is Map) MapRoad((r['a'] as num).toInt(), (r['b'] as num).toInt(), '${r['kind'] ?? 'main'}', r['bridge'] == true)
        ],
        landmarks = [
          for (final l in (j['landmarks'] as List?) ?? const [])
            if (l is Map) MapLandmark('${l['id']}', '${l['name']}', '${l['icon']}', Offset(_d(l['x']), _d(l['y'])), '${l['note'] ?? ''}')
        ],
        services = [
          for (final s in (j['services'] as List?) ?? const [])
            if (s is Map) MapServiceSlot('${s['id']}', (s['district'] as num).toInt(), Offset(_d(s['x']), _d(s['y'])), '${s['desc'] ?? ''}')
        ];

  static List<MapOval> _ovals(Object? v) => [
        for (final o in (v as List?) ?? const [])
          if (o is Map) MapOval('${o['name'] ?? ''}', Offset(_d(o['x']), _d(o['y'])), _d(o['rx']), _d(o['ry']))
      ];

  final Map<String, dynamic> j;
  /// Rezydencja (npc.HOME_DISTRICT) — start/meta kursów NPC.
  final int homeDistrict;
  // M1: malowana grafika regionu (sekcja "art" w map_data.json). Brak sekcji/pliku → wektorowy teren jak dotąd.
  Map get _art => (j['art'] as Map?) ?? const {};
  String? get artAsset => (_art['world'] as Map?)?['asset'] as String?;
  int get artMaxPx => ((_art['world'] as Map?)?['max_px'] as num?)?.toInt() ?? 2048;
  bool get artVectorRoads => _art['vector_roads'] != false;
  final double width, height;
  final Color background;
  final List<Offset> sea;
  final List<MapRiver> rivers;
  final List<MapOval> lakes, swamps;
  final List<MapRegion> regions;
  final List<MapDistrict> districts;
  final List<MapRoad> roads;
  final List<MapLandmark> landmarks;
  final List<MapServiceSlot> services;

  MapDistrict district(int id) => districts.firstWhere((m) => m.id == id, orElse: () => districts.first);
  MapServiceSlot? slot(String id) => services.where((s) => s.id == id).firstOrNull;
  /// Najkrótsza ścieżka po drogach (BFS) między dzielnicami — trasa auta na mapie.
  List<int> path(int from, int to) {
    final prev = <int, int>{from: from};
    final q = [from];
    while (q.isNotEmpty) {
      final cur = q.removeAt(0);
      if (cur == to) break;
      for (final r in roads) {
        final nxt = r.a == cur ? r.b : (r.b == cur ? r.a : null);
        if (nxt != null && !prev.containsKey(nxt)) {
          prev[nxt] = cur;
          q.add(nxt);
        }
      }
    }
    if (!prev.containsKey(to)) return [from, to];
    final out = [to];
    while (out.last != from) {
      out.add(prev[out.last]!);
    }
    return out.reversed.toList();
  }

  /// Punkty trasy: Rezydencja → sieć dróg → dojazd do usługi (powrót odwraca trasę).
  List<Offset> ridePoints(String serviceId, {required bool toWork}) {
    final slot = this.slot(serviceId);
    if (slot == null) return const [];
    final rawRoads = [for (final r in (j['roads'] as List?) ?? const []) if (r is Map && r['path'] is List) r];
    final lines = [for (final r in rawRoads) _pts(r['path'])];
    final access = <int>{for (var i = 0; i < rawRoads.length; i++) if (rawRoads[i]['a'] == slot.district || rawRoads[i]['b'] == slot.district) i};
    final pts = routeOnRoads(lines, district(homeDistrict).pos, slot.pos, destinationLines: access);
    return toWork ? pts : pts.reversed.toList();
  }

  /// Przebieg drogi a→b po grafice (map_data.json → roads[].path); brak → prosta linia.
  List<Offset> roadPath(int a, int b) {
    for (final r in (j['roads'] as List?) ?? const []) {
      if (r is! Map || r['path'] is! List) continue;
      final pts = _pts(r['path']);
      if (r['a'] == a && r['b'] == b) return pts;
      if (r['a'] == b && r['b'] == a) return pts.reversed.toList();
    }
    return [district(a).pos, district(b).pos];
  }

  MapRegion? regionOf(MapDistrict m) => regions.where((r) => r.id == m.region).firstOrNull;
}

/// Wczytanie raz na sesję (asset w paczce aplikacji — natychmiast, bez sieci).
final mapLayoutProvider = FutureProvider<MapLayout>((ref) async {
  final raw = await rootBundle.loadString('assets/data/map_data.json');
  return MapLayout((jsonDecode(raw) as Map).cast<String, dynamic>());
});
