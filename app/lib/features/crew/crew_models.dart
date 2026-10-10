// Modele ekranu „Ekipa” (GDD v3.2) — mapowanie odpowiedzi GET /npcs, /services, /state, /assistant.

int? _int(Object? v) => v is num ? v.toInt() : null;
double _dbl(Object? v) => v is num ? v.toDouble() : 0;

/// Katalog aut (lustro economy.GARAGE + TAXI_MULT z backendu) — nazwy i koszt Taxi liczony po stronie klienta.
class CarSpec {
  const CarSpec(this.id, this.name, this.fuel, this.fuelPrice, this.service, this.taxiMult, this.seats);
  final String id, name;
  final double fuel, fuelPrice, service, taxiMult;
  final int seats;

  /// Netto $/h na Taxi = 40 × mnożnik − paliwo (1 hop/h) − serwis (1%/h). Ta sama formuła co npc.taxi_net.
  double get taxiNetPerHour => 40 * taxiMult - fuel * fuelPrice - service / 100;
  double get taxiGrossPerHour => 40 * taxiMult;
}

const carCatalog = <String, CarSpec>{
  'dostawczak': CarSpec('dostawczak', 'Dostawczak', 4, 1.0, 300, 0.85, 1),
  'sedan': CarSpec('sedan', 'Sedan', 3, 1.5, 800, 1.15, 2),
  'van': CarSpec('van', 'Van Rodzinny', 5, 2.0, 1400, 1.25, 3),
  'furgonetka': CarSpec('furgonetka', 'Furgonetka', 5, 2.5, 2000, 1.0, 3),
  'suv': CarSpec('suv', 'SUV', 6, 3.0, 3000, 1.45, 4),
  'mistrz': CarSpec('mistrz', 'Mistrz Rankingu', 3, 2.0, 2000, 1.45, 4),
};

String carName(String? id) => id == null ? '' : (carCatalog[id]?.name ?? id);

/// Bonus auto-pilota za długość zmiany (D7: zostaje).
const shiftBonus = {2: 0, 4: 5, 8: 10, 12: 15};

class Npc {
  Npc(this.j);
  final Map<String, dynamic> j;

  int get id => _int(j['id']) ?? 0;
  String get name => '${j['name'] ?? ''}';
  String get avatar => '${j['avatar'] ?? 'npc-01'}';
  bool get isDriver => j['role'] == 'driver';
  double get energy => _dbl(j['energy']);
  double get mood => _dbl(j['mood']);
  double get satiety => _dbl(j['hunger']); // kolumna hunger = SYTOŚĆ
  bool get exhausted => j['exhausted'] == true;
  int get loyalty => _int(j['loyalty']) ?? 0;
  bool get loyal => j['loyal'] == true;
  String? get trait => j['trait'] as String?;
  String? get traitLabel => j['traitLabel'] as String?;
  String? get traitIcon => j['traitIcon'] as String?;
  String? get traitDesc => j['traitDesc'] as String?;
  bool get traitActive => j['traitActive'] != false;
  String? get phase => j['phase'] as String?; // to_work | working | to_home | sleeping
  String? get duty => j['duty'] as String?; // ferry | taxi
  String? get service => j['assigned_service_id'] as String?;
  int? get shiftEndsAt => _int(j['shiftEndsAt']);
  /// M4: start zmiany (backend: shiftStartedAt); stare odpowiedzi → koniec minus długość auto-pilota („8h”).
  int? get shiftStartedAt =>
      _int(j['shiftStartedAt']) ??
      (shiftEndsAt != null ? shiftEndsAt! - (int.tryParse('${j['autopilot_mode'] ?? ''}'.replaceAll('h', '')) ?? 8) * 3600000 : null);
  int? get phaseUntil => _int(j['phaseUntil']);
  String? get transport => j['transport'] as String?;
  String? get rideCar => j['rideCar'] as String?;
  int? get taxiUntil => _int(j['taxiUntil']);
  int get taxiCash => _int(j['taxiCash']) ?? 0;
  int get shiftCash => _int(j['shiftCash']) ?? 0;
  int? get rideId => _int(j['rideId']);
  bool get onShift => phase != null;
  bool get busy => onShift || duty != null;
  bool get canWork => !busy && energy >= 40;
}

/// M4: praca NPC w usłudze — przypisany pracownik + czas zakończenia zmiany (model dla panelu usługi na mapie).
class ServiceWork {
  ServiceWork(this.npc, this.startedAt, this.endsAt);
  final Npc npc;
  final int startedAt, endsAt;
  double progress(int now) => endsAt <= startedAt ? 1 : ((now - startedAt) / (endsAt - startedAt)).clamp(0.0, 1.0);
  int left(int now) => (endsAt - now).clamp(0, 2147483647);
  String get phaseLabel => switch (npc.phase) {
        'to_work' => '🚗 w drodze do pracy',
        'working' => '🛠️ pracuje',
        'to_home' => '🏠 wraca do domu',
        _ => '⏳ na zmianie',
      };
}

class Ride {
  Ride(this.j);
  final Map<String, dynamic> j;
  int get id => _int(j['id']) ?? 0;
  String get kind => '${j['kind']}'; // drop | pickup | taxi
  String get car => '${j['car']}';
  String get driverName => '${j['driverName'] ?? ''}';
  int get arriveAt => _int(j['arriveAt']) ?? 0;
  int get backAt => _int(j['backAt']) ?? 0;
  List<int> get passengers => ((j['passengers'] as List?) ?? const []).map((e) => _int(e) ?? 0).toList();
}

class ServiceInfo {
  ServiceInfo(this.j);
  final Map<String, dynamic> j;
  String get id => '${j['id']}';
  String get name => '${j['name']}';
  bool get unlocked => j['unlocked'] == true;
  double get demand => _dbl(j['demand'] ?? 1);
  double get rateNow => _dbl(j['rateNow'] ?? j['base_rate']);
  int get district => _int(j['d']) ?? 1;
}

class GarageCar {
  const GarageCar(this.id, this.fuel, this.wear);
  final String id;
  final double fuel, wear;
  CarSpec? get spec => carCatalog[id];
}

/// Plan asystenta: NPC + najlepsza opcja (usługa, prognoza wypłaty).
class AssistantTip {
  AssistantTip({required this.npcId, required this.npcName, required this.car, required this.option, required this.hours});
  final int npcId;
  final String npcName;
  final String? car;
  final Map<String, dynamic> option;
  final int hours;
  String get serviceId => '${option['service']}';
  String get serviceName => '${option['name']}';
  int get cash => _int(option['cash']) ?? 0;
  double get demand => _dbl(option['demand'] ?? 1);
  bool get burnout => option['burnout'] == true;
}

class CrewData {
  CrewData({required this.npcsJson, required this.services, required this.state, required this.assistant});
  final Map<String, dynamic> npcsJson;
  final List<ServiceInfo> services;
  final Map<String, dynamic> state; // obiekt „state” postaci (cash, garage, cars…)
  final Map<String, dynamic>? assistant;

  List<Npc> get npcs => ((npcsJson['npcs'] as List?) ?? const []).whereType<Map>().map((m) => Npc(m.cast())).toList();
  /// M4: kto pracuje w danej usłudze (tylko NPC na zmianie z czasem końca).
  List<ServiceWork> worksAt(String serviceId) => [
        for (final n in npcs)
          if (n.service == serviceId && n.onShift && n.shiftEndsAt != null) ServiceWork(n, n.shiftStartedAt ?? n.shiftEndsAt!, n.shiftEndsAt!),
      ];
  List<Ride> get rides => ((npcsJson['rides'] as List?) ?? const []).whereType<Map>().map((m) => Ride(m.cast())).toList();
  int get count => _int(npcsJson['count']) ?? 0;
  int get slots => _int(npcsJson['slots']) ?? 0;
  int get maxSlots => _int(npcsJson['maxSlots']) ?? 20;
  int? get nextCost => _int(npcsJson['nextCost']);
  bool get canRecruitHere => npcsJson['canRecruitHere'] == true;
  int get driversTotal => _int((npcsJson['drivers'] as Map?)?['total']) ?? 0;
  int get driversFree => _int((npcsJson['drivers'] as Map?)?['free']) ?? 0;
  int get cash => _int(state['cash']) ?? 0;

  List<GarageCar> get garage {
    final cars = (state['cars'] as Map?) ?? const {};
    return ((state['garage'] as List?) ?? const []).map((v) {
      final c = (cars[v] as Map?) ?? const {};
      return GarageCar('$v', c['fuel'] is num ? (c['fuel'] as num).toDouble() : 100, _dbl(c['wear']));
    }).toList();
  }

  /// Auta zajęte teraz przez kursy / Taxi.
  Set<String> get carsInUse => {for (final r in rides) r.car};

  List<ServiceInfo> get unlockedServices => services.where((s) => s.unlocked).toList()
    ..sort((a, b) => b.rateNow.compareTo(a.rateNow));

  String serviceName(String? id) => services.firstWhere((s) => s.id == id, orElse: () => ServiceInfo({'id': id, 'name': id ?? ''})).name;

  /// TOP 3 porady: najlepsza opcja każdego planu, posortowane wg prognozowanej wypłaty.
  List<AssistantTip> get tips {
    final a = assistant;
    if (a == null) return const [];
    final hours = _int(a['hours']) ?? 8;
    final out = <AssistantTip>[];
    for (final p in ((a['plans'] as List?) ?? const []).whereType<Map>()) {
      final opts = ((p['options'] as List?) ?? const []).whereType<Map>().toList();
      if (opts.isEmpty) continue;
      out.add(AssistantTip(npcId: _int(p['npc']) ?? 0, npcName: '${p['name']}', car: p['car'] as String?,
          option: opts.first.cast(), hours: hours));
    }
    out.sort((x, y) => y.cash.compareTo(x.cash));
    return out.take(3).toList();
  }

  List<String> get alerts => ((assistant?['alerts'] as List?) ?? const [])
      .whereType<Map>()
      .map((m) => '${m['text'] ?? ''}')
      .where((s) => s.isNotEmpty)
      .toList();
}
