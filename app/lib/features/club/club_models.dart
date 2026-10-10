/// Modele walki: raport z silnika 2.0 (combat.simultaneous) — rounds[].exchanges[].
library;

double _d(Object? v) => v is num ? v.toDouble() : 0;
int _i(Object? v) => v is num ? v.toInt() : 0;

/// Nazwy 5 statystyk w kolejności backendu (s['stats']).
const statNames = ['Siła', 'Inteligencja', 'Refleks', 'Charyzma', 'Spryt'];
const statIcons = ['💪', '🧠', '⚡', '🗣️', '🦊'];

/// Etykiety PL akcji ataku i reakcji obrońcy.
const actionLabels = {
  'PUNCH_FAST': 'Szybki cios',
  'PUNCH_HEAVY': 'Mocny cios',
  'KNEE_STRIKE': 'Kolano (riposta)',
  'GUARD_BLOCK': 'Gardą blokuje',
  'PARRY_HAND': 'Paruje dłonią',
  'DODGE_SIDE': 'Unik w bok',
  'TAKE_HIT': 'Przyjmuje cios',
};

/// Etykiety PL wyniku wymiany.
const resultLabels = {
  'FULL_HIT': 'Trafienie',
  'CRITICAL_HIT': 'KRYTYK!',
  'BLOCKED_PARTIAL': 'Częściowo zablokowany',
  'PARRIED': 'Sparowany',
  'MISSED': 'Pudło',
};

String actionPl(String code) => actionLabels[code] ?? code;
String resultPl(String code) => resultLabels[code] ?? code;

/// Tryb walki — wpływa na nagłówek i ekran nagród.
enum FightMode { pvp, dungeon, boxing, challenge }

/// Jedna wymiana ciosów.
class Exchange {
  Exchange(Map j, this.round)
      : striker = _i(j['striker']),
        action = '${j['attacker_action'] ?? ''}',
        reaction = '${j['defender_reaction'] ?? ''}',
        result = '${j['result'] ?? ''}',
        damage = _d(j['damage']),
        hp = [for (final v in (j['hp'] as List?) ?? const [0, 0]) _d(v)];
  final int round, striker; // striker: 0 = lewa strona (gracz), 1 = przeciwnik
  final String action, reaction, result;
  final double damage;
  final List<double> hp; // HP obu stron PO wymianie
  bool get landed => damage > 0;
  bool get critical => result == 'CRITICAL_HIT';
}

/// Raport jednej walki (PvP / Loch / pojedynek turnieju).
class FightReport {
  FightReport(this.j, {this.title, List<String>? names, List<List<double>>? stats})
      : names = names ?? [for (final n in (j['names'] as List?) ?? const ['Ty', 'Przeciwnik']) '$n'],
        stats = stats ??
            [
              for (final s in (j['stats'] as List?) ?? const [])
                [for (final v in (s as List?) ?? const []) _d(v)]
            ];
  final Map<String, dynamic> j;
  final String? title;
  final List<String> names;
  final List<List<double>> stats; // może być puste (brak danych)

  List<double> get hpStart => [for (final v in (j['hpStart'] as List?) ?? const [100, 100]) _d(v)];
  List<double> get finalHp => [for (final v in (j['finalHp'] as List?) ?? const [0, 0]) _d(v)];
  int? get winner => j['winner'] is num ? (j['winner'] as num).toInt() : null; // null = remis
  List<String> get classes => [for (final c in (j['classes'] as List?) ?? const ['', '']) '${c ?? ''}'];
  List<double> get ratingChanges => [for (final v in (j['ratingChanges'] as List?) ?? const []) _d(v)];

  /// Wszystkie wymiany w kolejności (spłaszczone rundy) + zmęczenie per runda.
  late final List<Exchange> exchanges = [
    for (final r in (j['rounds'] as List?) ?? const [])
      if (r is Map)
        for (final e in (r['exchanges'] as List?) ?? const [])
          if (e is Map) Exchange(e, _i(r['r'])),
  ];
  late final Map<int, double> fatigue = {
    for (final r in (j['rounds'] as List?) ?? const []) if (r is Map) _i(r['r']): _d(r['fatigue']),
  };
}

/// Nagrody po walce (wspólny format dla trybów).
class FightRewards {
  const FightRewards({this.cash = 0, this.xp = 0, this.drops = const [], this.extra = const [], this.message});
  final int cash, xp;
  final List<String> drops, extra;
  final String? message;
}

/// Pakiet do FightScreen: jedna lub więcej walk (turniej = seria) + nagrody.
class FightSession {
  const FightSession({required this.mode, required this.reports, this.rewards = const FightRewards(), this.title = '', this.dungeonMode});
  final FightMode mode;
  /// QA 2: tryb Lochu (normal/hard/nightmare) → przycisk „Następne piętro” na ekranie wyników.
  final String? dungeonMode;
  final List<FightReport> reports;
  final FightRewards rewards;
  final String title;
}
