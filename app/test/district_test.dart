import 'package:city_empire/features/district/district_providers.dart';
import 'package:city_empire/features/district/district_screen.dart';
import 'package:city_empire/features/district/district_visual.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

DistrictData fixture({String? building, int level = 1}) => DistrictData({
  'serverTime': DateTime.now().millisecondsSinceEpoch,
  'world': {'speed': 1},
  'state': {
    'cash': 100000,
    'buildings': {'residence': level, 'cafe': 1},
    if (building != null) 'construction': {'building': building, 'target': 2, 'startedAt': DateTime.now().millisecondsSinceEpoch, 'endsAt': DateTime.now().millisecondsSinceEpoch + 60000},
  },
  'catalog': {
    'buildings': {'residence': {'name': 'Rezydencja'}, 'cafe': {'name': 'Kawiarnia'}},
    'buildingMaxes': {'residence': 5, 'cafe': 10},
    'buildingCostsBy': {'residence': [0, 100, 200, 300, 400]},
  },
});

void main() {
  test('postęp i czas są ograniczone przed startem i po końcu', () {
    final c = Construction(building: 'residence', target: 2, startedAt: 1000, endsAt: 11000);
    expect(c.progress(0), 0); expect(c.progress(6000), .5); expect(c.progress(20000), 1);
    expect(c.left(20000), Duration.zero);
  });
  test('odliczanie używa czasu serwera mimo złego zegara urządzenia', () {
    final d = DistrictData({'serverTime': 100000, 'state': {'construction': {'building': 'cafe', 'target': 2, 'startedAt': 90000, 'endsAt': 160000}}});
    expect(d.construction!.left().inSeconds, inInclusiveRange(59, 60));
    expect(d.construction!.done, false);
  });
  test('nieznany budynek nie otwiera uszkodzonego panelu', () {
    expect(fixture(building: 'unknown').construction, isNull);
  });
  test('warianty obejmują wszystkie poziomy', () {
    for (final max in [1, 5, 7, 10]) {
      for (var level = 1; level <= max; level++) {
        expect(buildingTier(level, max), inInclusiveRange(1, 3));
      }
    }
    expect(buildingTier(5, 5), 3);
  });
  test('format czasu', () {
    expect(fmtLeft(const Duration(seconds: 45)), '45 s');
    expect(fmtLeft(const Duration(minutes: 65)), '1 h 05 min');
  });
  for (final building in ['residence', 'cafe']) {
    testWidgets('budowa $building blokuje rozbudowę i nie podnosi poziomu w karcie', (t) async {
      final d = fixture(building: building);
      await t.pumpWidget(ProviderScope(child: MaterialApp(home: Scaffold(body: BuildingCard(b: d.byId('residence'), d: d, busy: const {}, onUpgrade: () {}, construction: d.construction)))));
      expect(find.text('Lvl 1/5'), findsOneWidget);
      if (building == 'residence') {
        expect(find.byType(ConstructionPill), findsOneWidget);
        expect(find.byKey(const Key('upgrade-residence')), findsNothing);
      } else {
        expect(t.widget<OutlinedButton>(find.byKey(const Key('upgrade-residence'))).onPressed, isNull);
      }
      await t.pumpWidget(const SizedBox());
    });
  }
  testWidgets('błąd pobierania panelu daje ponowienie zamiast wiecznego spinnera', (t) async {
    await t.pumpWidget(ProviderScope(overrides: [districtProvider.overrideWith((ref) async => throw Exception('offline'))], child: const MaterialApp(home: Scaffold(body: BuildingPanel(id: 'residence')))));
    await t.pumpAndSettle();
    expect(find.text('Spróbuj ponownie'), findsOneWidget);
    expect(find.text('Zamknij'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });
}
