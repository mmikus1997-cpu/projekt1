import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:city_empire/features/map/map_layout.dart';
import 'package:city_empire/features/map/map_routes.dart';
import 'package:city_empire/features/map/map_providers.dart';
import 'package:city_empire/features/district/district_providers.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('auto nie jedzie do pinezki przez teren poza ulicą', () {
    final route = routeOnRoads([[const Offset(0, 0), const Offset(100, 0)]], const Offset(10, 0), const Offset(70, 40));
    expect(route, [const Offset(10, 0), const Offset(70, 0)]);
  });
  test('brak połączenia oznacza brak animacji, nie skrót', () {
    expect(routeOnRoads([[Offset.zero, const Offset(10, 0)], [const Offset(100, 0), const Offset(110, 0)]], Offset.zero, const Offset(110, 0)), isEmpty);
  });
  test('pusta geometria i odcinki o zerowej długości', () {
    expect(routeOnRoads([], Offset.zero, const Offset(5, 5)), isEmpty);
    expect(routeOnRoads([[Offset.zero, Offset.zero]], Offset.zero, const Offset(5, 5)), isEmpty);
  });
  test('najkrótszy dystans zamiast najmniejszej liczby ulic', () {
    final route = routeOnRoads([
      [Offset.zero, const Offset(0, 100), const Offset(100, 100), const Offset(100, 0)],
      [Offset.zero, const Offset(50, 0), const Offset(100, 0)],
    ], Offset.zero, const Offset(100, 0));
    expect(route, [Offset.zero, const Offset(50, 0), const Offset(100, 0)]);
  });
  test('dojazd pozostaje przy drogach właściwej dzielnicy', () {
    final route = routeOnRoads([
      [Offset.zero, const Offset(100, 0)],
      [Offset.zero, const Offset(0, 100), const Offset(100, 100)],
    ], Offset.zero, const Offset(50, 1), destinationLines: {1});
    expect(route.last, const Offset(0, 1));
  });
  final raw = jsonDecode(File('assets/data/map_data.json').readAsStringSync()) as Map<String, dynamic>;
  final layout = MapLayout(raw);
  for (final slot in layout.services) {
    test('trasa ${slot.id}: wszystkie odcinki na drogach, powrót symetryczny', () {
      final roadSegments = <(Offset, Offset)>[];
      for (final r in raw['roads']) {
        final points = [for (final p in r['path']) Offset((p[0] as num).toDouble(), (p[1] as num).toDouble())];
        for (var i = 1; i < points.length; i++) { roadSegments.add((points[i - 1], points[i])); }
      }
      bool on(Offset p, Offset a, Offset b) => ((p - a).distance + (p - b).distance - (a - b).distance).abs() < .001;
      final route = layout.ridePoints(slot.id, toWork: true);
      expect(route.length, greaterThanOrEqualTo(2));
      expect(layout.ridePoints(slot.id, toWork: false), route.reversed.toList());
      for (var i = 1; i < route.length; i++) {
        expect(roadSegments.any((s) => on(route[i - 1], s.$1, s.$2) && on(route[i], s.$1, s.$2)), isTrue, reason: '$i: ${route[i - 1]} -> ${route[i]}');
      }
    });
  }
  test('mapa używa czasu serwera do odliczania', () {
    final d = MapData(layout: layout, district: DistrictData({'serverTime': 100000}), services: [], demandTop: [], tips: [], changesAt: 160000);
    expect(d.nowMs, inInclusiveRange(100000, 101000));
  });
}
