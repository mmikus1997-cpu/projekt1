import 'dart:math' as math;

/// Modele danych. Na start ręczne fromJson (tolerancyjne na brakujące pola);
/// przejście na Freezed (pakiety już dodane) przy stabilizacji API.
num _n(Object? v) => v is num ? v : 0;

class User {
  const User({required this.id, required this.username, required this.role});
  final int id;
  final String username;
  final String role;
  factory User.fromJson(Map<String, dynamic> j) =>
      User(id: _n(j['id']).toInt(), username: '${j['username'] ?? ''}', role: '${j['role'] ?? 'player'}');
}

class WorldInfo {
  const WorldInfo({
    required this.id,
    required this.name,
    required this.kind,
    required this.registrationOpen,
    required this.speed,
    required this.announcement,
    required this.eraLabel,
    this.characterName,
  });
  final int id;
  final String name;
  final String kind;
  final bool registrationOpen;
  final num speed;
  final String announcement;
  final String eraLabel;
  final String? characterName;
  bool get hasCharacter => characterName != null;

  factory WorldInfo.fromJson(Map<String, dynamic> j) {
    final ch = j['character'];
    final era = j['era'];
    return WorldInfo(
      id: _n(j['id']).toInt(),
      name: '${j['name'] ?? ''}',
      kind: '${j['kind'] ?? 'standard'}',
      registrationOpen: j['registration_open'] == 1 || j['registration_open'] == true,
      speed: _n(j['speed']),
      announcement: '${j['announcement'] ?? ''}',
      eraLabel: era is Map ? '${era['label'] ?? ''}' : '',
      characterName: ch is Map ? '${ch['nickname'] ?? ''}' : null,
    );
  }
}

class NpcSummary {
  const NpcSummary({required this.name, required this.status, required this.energy, required this.mood, required this.satiety});
  final String name;
  final String status;
  final double energy, mood, satiety; // 0–100 (3 emocje/potrzeby z GDD 2.3)
  factory NpcSummary.fromJson(Map<String, dynamic> j) => NpcSummary(
        name: '${j['name'] ?? j['nickname'] ?? 'NPC'}',
        status: '${j['status'] ?? 'idle'}',
        energy: _n(j['energy']).toDouble(),
        mood: _n(j['mood']).toDouble(),
        satiety: _n(j['hunger'] ?? j['satiety']).toDouble(), // backend: hunger = SYTOŚĆ
      );
}

/// GET /api/worlds/{wid}/dashboard (Etap 8.6) — wszystko w jednym żądaniu.
class DashboardData {
  DashboardData(this.raw);
  final Map<String, dynamic> raw;

  Map<String, dynamic> get _packet => (raw['state'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> get _s => (_packet['state'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> get _ch => (_packet['character'] as Map?)?.cast<String, dynamic>() ?? const {};

  static const maxEnergy = 240.0;
  /// QA 5: maks. energia rośnie z Łucznictwem (+3/6/10% do północy) — backend liczy state.energyMax.
  double get energyMax => _s['energyMax'] is num ? (_s['energyMax'] as num).toDouble() : maxEnergy;
  num get cash => _n(_s['cash']);
  double get energy => _n(_s['energy']).toDouble();
  num get xp => _n(_s['xp']);

  /// Ten sam wzór co server/economy.py: level(xp).
  int get level => ((1 + math.sqrt(1 + 8 * xp / 100)) ~/ 2);
  String get nickname => '${_ch['nickname'] ?? ''}';
  String get classType => '${_ch['classType'] ?? ''}';
  num get rating => _n(_ch['rating']);
  int get unread => _n(_packet['eventsUnread']).toInt() + _n(_packet['dmUnread']).toInt();
  int get eventsUnread => _n(_packet['eventsUnread']).toInt();
  int get dmUnread => _n(_packet['dmUnread']).toInt();
  String get worldName => '${(_packet['world'] as Map?)?['name'] ?? ''}';

  // Skarbce idle
  Map<String, dynamic> get vaults => (raw['vaults'] as Map?)?.cast<String, dynamic>() ?? const {};
  num get vaultTotal => _n(vaults['total']);
  Map<String, num> get buildingVaults =>
      ((vaults['buildings'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', _n(v)));
  num get businessVault => _n(vaults['business']);

  // NPC
  Map<String, dynamic> get npc => (raw['npc'] as Map?)?.cast<String, dynamic>() ?? const {};
  int get npcCount => _n(npc['count']).toInt();
  List<NpcSummary> get npcs =>
      ((npc['list'] as List?) ?? const []).whereType<Map>().map((m) => NpcSummary.fromJson(m.cast())).toList();

  // Battle Pass
  Map<String, dynamic> get bp => (raw['battlepass'] as Map?)?.cast<String, dynamic>() ?? const {};
  int get bpLevel => _n(bp['level']).toInt();
  int get bpLevels => _n(bp['levels']).toInt() == 0 ? 30 : _n(bp['levels']).toInt();
  int get bpXp => _n(bp['xp']).toInt();
  bool get bpPremium => bp['premium'] == true;
  String get bpSeason => '${bp['season'] ?? ''}';
  String get bpTheme => '${bp['theme'] ?? ''}';

  // Wydarzenia / asystent / staż
  Map<String, dynamic>? get timedEvent => ((raw['events'] as Map?)?['timed'] as Map?)?.cast<String, dynamic>();
  List<String> get alerts => (((raw['assistant'] as Map?)?['alerts'] as List?) ?? const [])
      .whereType<Map>()
      .map((a) => '${a['text'] ?? ''}')
      .where((t) => t.isNotEmpty)
      .toList();
  int get activeDays => _n((raw['milestones'] as Map?)?['activeDays']).toInt();
  int? get nextMilestone {
    final n = (raw['milestones'] as Map?)?['next'];
    return n is Map ? _n(n['days']).toInt() : null;
  }

  /// 💎 i sojusz — pola dodane do /dashboard na potrzeby HUD i karty sojuszu.
  int get diamonds => _n(raw['diamonds']).toInt();
  /// Katalog gry z /dashboard (state.catalog): budynki sojuszu, koszty, auta itd.
  Map<String, dynamic> get catalog => (_packet['catalog'] as Map?)?.cast<String, dynamic>() ?? const {};
  // ── Etap 1 UI v2: „Co się wydarzyło” + plakietki menu (dane z istniejącego /dashboard)
  /// state.away: minuty nieobecności (backend ustawia po >30 min bez akcji), inaczej null.
  int? get awayMinutes {
    final a = _packet['away'];
    return a is Map ? _n(a['minutes']).toInt() : null;
  }
  Map<String, int> get npcByStatus =>
      ((npc['byStatus'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', _n(v).toInt()));
  /// Wypaleni NPC (burnout, GDD 2.3).
  List<String> get burntNpcs => ((npc['list'] as List?) ?? const [])
      .whereType<Map>()
      .where((m) => m['exhausted'] == true)
      .map((m) => '${m['name'] ?? 'NPC'}')
      .toList();
  /// Auta ze zużyciem 100% (economy.worn) — wymagają serwisu.
  List<String> get brokenCars => ((_s['cars'] as Map?) ?? const {})
      .entries
      .where((e) => e.value is Map && _n((e.value as Map)['wear']) >= 100)
      .map((e) => '${e.key}')
      .toList();
  /// Ostatnie nieprzeczytane zdarzenia (tekst z payload).
  List<String> get recentEvents => ((_packet['eventsRecent'] as List?) ?? const [])
      .whereType<Map>()
      .where((e) => e['read'] != true)
      .map((e) => '${(e['payload'] as Map?)?['text'] ?? ''}')
      .where((t) => t.isNotEmpty)
      .toList();

  // ── Etap 4 UI v2: żywa mapa + plakietki z liczbami (dalej tylko /dashboard)
  List<Map<String, dynamic>> get _npcList => ((npc['list'] as List?) ?? const []).whereType<Map>().map((m) => m.cast<String, dynamic>()).toList();

  /// Aktywne kursy NPC (dojazd do pracy / powrót do Rezydencji).
  List<NpcRide> get rides => [
        for (final m in _npcList)
          if ((m['phase'] == 'to_work' || m['phase'] == 'to_home') && m['phaseUntil'] is num && m['travelMs'] is num && m['assigned_service_id'] != null)
            NpcRide(
              npcId: _n(m['id']).toInt(),
              name: '${m['name'] ?? 'NPC'}',
              toWork: m['phase'] == 'to_work',
              serviceId: '${m['assigned_service_id']}',
              arriveAt: _n(m['phaseUntil']).toInt(),
              departAt: _n(m['phaseUntil']).toInt() - _n(m['travelMs']).toInt(),
              transport: '${m['transport'] ?? 'car'}',
              car: m['rideCar'] as String?,
            ),
      ];

  /// Wypełnienie skarbców 0–1 (pojemność = stawka poziomu × tempo świata × godziny, jak DistrictData.vault).
  Map<String, double> get vaultFills {
    final cfg = (catalog['buildingVaults'] as Map?) ?? const {};
    final lv = (_s['buildings'] as Map?) ?? const {};
    final speed = _n((_packet['world'] as Map?)?['speed']).toDouble().clamp(1, 1e9);
    final out = <String, double>{};
    for (final e in buildingVaults.entries) {
      final c = cfg[e.key] as Map?;
      final level = _n(lv[e.key]).toInt();
      final rates = (c?['rates'] as List?) ?? const [];
      if (c == null || level < 1 || level > rates.length) continue;
      final cap = _n(rates[level - 1]) * speed * _n(c['hours']);
      out[e.key] = cap <= 0 ? 0 : (e.value / cap).clamp(0, 1).toDouble();
    }
    return out;
  }

  /// NPC wymagający uwagi: wypaleni albo wszystkie 3 potrzeby < 35%.
  List<String> get warnNpcs => [
        for (final m in _npcList)
          if (m['exhausted'] == true || (_n(m['energy']) < 35 && _n(m['mood']) < 35 && _n(m['hunger']) < 35)) '${m['name'] ?? 'NPC'}'
      ];

  String carName(String id) {
    final m = ((catalog['vehicles'] as List?) ?? const []).whereType<Map>().where((x) => x['id'] == id).firstOrNull;
    return '${m?['name'] ?? id}';
  }

  /// Czy pokazać „Co się wydarzyło”: jest co odebrać albo coś się zepsuło.
  bool get hasNews => vaultTotal >= 1 || crewEarned >= 1 || brokenCars.isNotEmpty;

  /// Zarobki bieżących zmian ekipy (shiftCash) — trafiają na konto przy rozliczeniu.
  num get crewEarned => _npcList.fold<num>(0, (s, m) => s + _n(m['shiftCash']));

  AllianceSummary? get alliance {
    final a = raw['alliance'];
    return a is Map ? AllianceSummary.fromJson(a.cast()) : null;
  }
}

class AllianceSummary {
  const AllianceSummary({required this.id, required this.name, required this.tag, required this.role,
      required this.members, required this.fund, this.federationName, this.federationOrgs = 0});
  final int id;
  final String name, tag, role;
  final int members;
  final num fund;
  final String? federationName;
  final int federationOrgs;
  factory AllianceSummary.fromJson(Map<String, dynamic> j) {
    final f = j['federation'];
    return AllianceSummary(
      id: _n(j['id']).toInt(),
      name: '${j['name'] ?? ''}',
      tag: '${j['tag'] ?? ''}',
      role: '${j['role'] ?? 'member'}',
      members: _n(j['members']).toInt(),
      fund: _n(j['fund']),
      federationName: f is Map ? '${f['name'] ?? ''}' : null,
      federationOrgs: f is Map ? _n(f['orgs']).toInt() : 0,
    );
  }
}


/// Kurs NPC na mapie: Rezydencja ⇄ lokacja usługowa, czas wyjazdu/przyjazdu z backendu (ms).
class NpcRide {
  const NpcRide({required this.npcId, required this.name, required this.toWork, required this.serviceId,
      required this.departAt, required this.arriveAt, required this.transport, this.car});
  final int npcId;
  final String name, serviceId, transport; // transport: car | bus | hitchhike
  final bool toWork;
  final int departAt, arriveAt;
  final String? car;
  double progress(int now) => arriveAt <= departAt ? 1 : ((now - departAt) / (arriveAt - departAt)).clamp(0.0, 1.0);
}
