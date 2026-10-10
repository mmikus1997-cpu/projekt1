import 'package:city_empire/features/crew/crew_models.dart';
import 'package:city_empire/features/crew/crew_providers.dart';
import 'package:city_empire/features/district/district_providers.dart';
import 'package:city_empire/features/map/map_layout.dart';
import 'package:city_empire/features/map/map_providers.dart';
import 'package:city_empire/features/map/map_panel.dart';
import 'package:city_empire/features/map/map_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('pozostały czas zmiany nie jest ujemny ani zależny od przesunięcia bitowego JS', () {
    final work = ServiceWork(Npc({'id': 1, 'phase': 'working'}), 1000, 11000);
    expect(work.left(6000), 5000); expect(work.left(12000), 0);
    expect(work.progress(6000), .5); expect(work.progress(12000), 1);
  });
  testWidgets('panel 320px: pracownik, postęp i odświeżenie zakończonej zmiany', (t) async {
    t.view.physicalSize = const Size(320, 740);
    t.view.devicePixelRatio = 1;
    addTearDown(t.view.resetPhysicalSize); addTearDown(t.view.resetDevicePixelRatio);
    final layout = MapLayout({'board': {'width': 1600, 'height': 1120}, 'districts': [{'id': 3, 'name': 'Centrum', 'x': 100, 'y': 100}], 'services': [{'id': 'kawiarnia', 'district': 3, 'x': 110, 'y': 110, 'desc': 'Usługa'}]});
    final data = MapData(layout: layout, district: DistrictData({'serverTime': 100000}), services: [MapService({'id': 'kawiarnia', 'name': 'Kawiarnia', 'd': 3, 'unlocked': true, 'demand': 1, 'rateNow': 30})], demandTop: [], tips: [], changesAt: 200000);
    var reads = 0;
    await t.pumpWidget(ProviderScope(overrides: [crewProvider.overrideWith((ref) async {
      reads++;
      return CrewData(npcsJson: {'npcs': reads == 1 ? [{'id': 1, 'name': 'Pracownik QA z długim nazwiskiem', 'phase': 'working', 'assigned_service_id': 'kawiarnia', 'shiftStartedAt': 90000, 'shiftEndsAt': 99999}] : []}, services: [], state: {}, assistant: null);
    })], child: MaterialApp(home: Scaffold(body: MapPanelContent(sel: const MapSelection(MapSelKind.service, 'kawiarnia'), d: data)))));
    await t.pump(); await t.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const Key('work-1')), findsOneWidget);
    expect(find.byKey(const Key('work-progress')), findsOneWidget);
    expect(t.takeException(), isNull);
    await t.pump(const Duration(seconds: 1)); await t.pump(); await t.pump(const Duration(milliseconds: 100));
    expect(reads, 2); expect(find.byKey(const Key('work-1')), findsNothing);
    expect(find.text('Wyślij NPC do pracy'), findsOneWidget);
    expect(t.takeException(), isNull);
    await t.pumpWidget(const SizedBox());
  });
}
