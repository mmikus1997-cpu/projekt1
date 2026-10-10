import 'dart:async';
import 'dart:math' as math;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';
import 'club_models.dart';
import 'gear_providers.dart';

int _i(Object? v) => v is num ? v.toInt() : 0;
double _d(Object? v) => v is num ? v.toDouble() : 0;

class ClubData {
  ClubData({required this.state, required this.targets, required this.dailyUsed, required this.sports, required this.level});
  final Map<String, dynamic> state; // GET /state (pełny payload)
  final List<Map<String, dynamic>> targets; // GET /pvp/targets
  final int dailyUsed; // GET /pvp → daily_used
  final Map<String, dynamic> sports; // GET /sports2
  final int level;

  Map<String, dynamic> get s => (state['state'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> get character => (state['character'] as Map?)?.cast<String, dynamic>() ?? const {};
  String get nickname => '${character['nickname'] ?? 'Ty'}';
  String? get classType => character['classType'] as String?;
  double get energy => _d(s['energy']);
  double get cash => _d(s['cash']);
  List<double> get stats => [for (final v in (s['stats'] as List?) ?? const []) _d(v)];
  /// QA 3: ceny treningu (50 $ + stat × 15 $, rabat Charyzmy) liczone przez backend.
  List<int> get gymCosts => [for (final v in ((state['catalog'] as Map?)?['gymCosts'] as List?) ?? const []) _i(v)];
  List<Map<String, dynamic>> get training => [for (final t in (s['training'] as List?) ?? const []) if (t is Map) t.cast<String, dynamic>()];
  Map<String, dynamic> get dungeon => (state['dungeon'] as Map?)?.cast<String, dynamic>() ?? const {};
  Map<String, dynamic> mode(String m) => ((dungeon['modes'] as Map?)?[m] as Map?)?.cast<String, dynamic>() ?? const {};
  // Poziom PvP i ewolucje (GET /state → character.evolution)
  Map<String, dynamic> get evolution => (character['evolution'] as Map?)?.cast<String, dynamic>() ?? const {};
  int get pvpLevel => _i(evolution['pvpLevel'] ?? character['pvpLevel']);
  int get pvpPoints => _i(evolution['pvpPoints']);
  int? get pvpNextAt => evolution['pvpNextAt'] == null ? null : _i(evolution['pvpNextAt']);
  Map<String, dynamic>? get evo1 => (evolution['evolution1'] as Map?)?.cast<String, dynamic>();
  Map<String, dynamic>? get evo2 => (evolution['evolution2'] as Map?)?.cast<String, dynamic>();
  Map<String, dynamic>? get nextEvolution => (evolution['next'] as Map?)?.cast<String, dynamic>();
  bool get canEvolve => nextEvolution?['available'] == true;
  bool get traveling => (state['travelInfo'] as Map?)?['travel'] != null;
  static const dailyLimit = 15; // RANKED_DAILY (app.py)
}

final clubProvider = FutureProvider.autoDispose<ClubData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final b = '/api/worlds/$wid';
  final r = await Future.wait([
    api.get('$b/state'),
    api.get('$b/pvp/targets').catchError((_) => <String, dynamic>{}),
    api.get('$b/pvp').catchError((_) => <String, dynamic>{}),
    api.get('$b/sports2').catchError((_) => <String, dynamic>{}),
  ]);
  // poziom z XP — ten sam wzór co server/economy.py level(xp) i HUD
  final xp = _d(((r[0]['state'] as Map?) ?? const {})['xp']);
  final lvl = (1 + math.sqrt(1 + 8 * xp / 100)) ~/ 2;
  return ClubData(
    state: r[0],
    targets: [for (final t in (r[1]['targets'] as List?) ?? const []) if (t is Map) t.cast<String, dynamic>()],
    dailyUsed: _i(r[2]['daily_used']),
    sports: r[3],
    level: lvl,
  );
});

/// QA 5: psiarnia, okna 4 h (agility / jazda konna), koń i stajnia — GET /sports3.
final sports3Provider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  return ref.watch(apiClientProvider).get('/api/worlds/$wid/sports3');
});

/// Globalna preferencja prędkości animacji walki: 1, 2, 4 (0 = zawsze pomijaj).
final fightSpeedProvider = StateProvider<int>((ref) => 1);

/// Wynik akcji klubu: komunikat albo sesja walki do odtworzenia.
class ClubResult {
  const ClubResult(this.message, {this.ok = true, this.fight});
  final String message;
  final bool ok;
  final FightSession? fight;
}

class ClubActions {
  ClubActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<ClubResult> _run(Future<ClubResult> Function() f) async {
    try {
      return await f();
    } on ApiException catch (e) {
      return ClubResult(e.message, ok: false);
    } finally {
      _ref.invalidate(clubProvider);
      _ref.invalidate(dashboardProvider);
      _ref.invalidate(gearProvider); // QA 2: dropy z walk od razu widoczne w Ekwipunku
    }
  }

  Future<ClubResult> pickClass(String cls) => _run(() async {
        final r = await _api.post('$_base/class', {'class_type': cls});
        return ClubResult('${r['message']}');
      });

  /// Ewolucja klasy wg poziomu PvP (etap I od PvP 5, etap II od PvP 10).
  Future<ClubResult> evolve(String code) => _run(() async {
        final r = await _api.post('$_base/pvp/evolve', {'choice': code});
        return ClubResult('${r['message']}');
      });

  /// PvP: atak rozstrzyga się od razu (Klasa = Taktyka) → raport do FightScreen.
  Future<ClubResult> attack(int targetId, String targetName) => _run(() async {
        final r = await _api.post('$_base/pvp/attack/$targetId', {});
        final rep = FightReport((r['report'] as Map).cast<String, dynamic>());
        final mine = ((r['rewards'] as List?)?.first as Map?) ?? const {};
        return ClubResult('Walka z $targetName', fight: FightSession(
          mode: FightMode.pvp,
          title: '⚔️ Pojedynek rankingowy',
          reports: [rep],
          rewards: FightRewards(
            cash: _i(mine['cash']),
            xp: _i(mine['xp']),
            extra: [
              if (rep.ratingChanges.isNotEmpty) 'Elo ${rep.ratingChanges[0] >= 0 ? '+' : ''}${rep.ratingChanges[0].toStringAsFixed(1)}',
              if (_i(mine['prestige']) > 0) '+${mine['prestige']} Punkt Prestiżu',
            ],
          ),
        ));
      });

  /// Loch: ustawia lokację „Brama Lochu” (wymóg backendu), potem walka o następne piętro.
  Future<ClubResult> dungeon(String mode) => _run(() async {
        final st = await _api.get('$_base/state');
        if ((st['character'] as Map?)?['currentLocation'] != 'brama-lochow') {
          await _api.post('$_base/location', {'location': 'brama-lochow'});
        }
        final r = await _api.post('$_base/dungeon/floor', {'mode': mode});
        final rep = FightReport((r['report'] as Map).cast<String, dynamic>());
        final rw = (r['rewards'] as Map?) ?? const {};
        return ClubResult('${r['message']}', fight: FightSession(
          mode: FightMode.dungeon,
          dungeonMode: mode,
          title: '🐉 Loch ${mode[0].toUpperCase()}${mode.substring(1)} · piętro ${r['floor']}${r['boss'] == true ? ' · BOSS' : ''}',
          reports: [rep],
          rewards: FightRewards(
            cash: _i(rw['cash']),
            xp: _i(rw['xp']),
            drops: [
              for (final d in (r['drops'] as List?) ?? const []) if (d is Map) '🎁 ${d['name']}${d['to'] == 'backpack' ? ' (plecak)' : ''}',
              for (final d in (r['cosmetics'] as List?) ?? const []) if (d is Map) '✨ ${d['name']}',
              for (final d in (r['pets'] as List?) ?? const []) if (d is Map) '🐾 ${d['name']}',
            ],
            message: '${r['message']}',
          ),
        ));
      });

  /// Boks / MMA: turniej (seria walk) → wszystkie pojedynki do odtworzenia po kolei.
  Future<ClubResult> tournament(String me) => _run(() async {
        final r = await _api.post('$_base/sports/tournament', {});
        final prize = (r['prize'] as Map?) ?? const {};
        return ClubResult('${r['message']}', fight: FightSession(
          mode: FightMode.boxing,
          title: '🥊 Turniej bokserski',
          reports: [
            for (final (i, b) in ((r['rounds'] as List?) ?? const []).indexed)
              if (b is Map) FightReport(b.cast<String, dynamic>(), title: 'Walka ${i + 1}', names: [me, '${b['opponent']}']),
          ],
          rewards: FightRewards(cash: _i(prize['cash']), xp: _i(prize['xp']), message: '${r['message']}'),
        ));
      });


  // QA 5: nowe mini-gry — odpowiedź backendu ma gotowy komunikat; każda akcja odświeża też sports3Provider
  Future<ClubResult> _sport(String path, Map<String, dynamic> body) => _run(() async {
        try {
          final r = await _api.post('$_base$path', body);
          return ClubResult('${r['message'] ?? 'OK'}${r['newRecord'] == true ? ' · REKORD!' : ''}');
        } finally {
          _ref.invalidate(sports3Provider);
        }
      });
  Future<ClubResult> agility({bool treat = false}) => _sport('/sports/agility', {'treat': treat});
  Future<ClubResult> riding() => _sport('/sports/riding', {});
  Future<ClubResult> archery({bool skip = false}) => _sport('/sports/archery', {'skip': skip});
  Future<ClubResult> swim({bool skip = false}) => _sport('/sports/swim', {'skip': skip});
  Future<ClubResult> dogBuy(String breed) => _sport('/sports/dog/buy', {'breed': breed});
  Future<ClubResult> dogPick(String key) => _sport('/sports/dog/pick', {'key': key});
  Future<ClubResult> dogTrain(String stat) => _sport('/sports/dog/train', {'stat': stat});
  Future<ClubResult> buyHorse(String id) => _sport('/racing/horse', {'horse': id});
  Future<ClubResult> pickHorse(String key) => _sport('/racing/stable', {'key': key});

  Future<ClubResult> train(int stat) => _run(() async {
        final r = await _api.post('$_base/actions', {'action': 'train', 'stat': stat});
        return ClubResult('${r['message'] ?? '💪 ${statNames[stat]} +1'}');
      });
  Future<ClubResult> claimTraining(int id) => _run(() async {
        final r = await _api.post('$_base/actions', {'action': 'claim_training', 'task_id': id});
        return ClubResult('${r['message'] ?? 'Odebrano'}');
      });
}

final clubActionsProvider = Provider<ClubActions>((ref) => ClubActions(ref));

// ---------------------------------------------------------------------------
// Odtwarzanie walki: indeks bieżącej wymiany w bieżącej walce sesji.
// ---------------------------------------------------------------------------
class FightState {
  const FightState({this.bout = 0, this.step = 0, this.done = false, this.finished = false});
  final int bout; // która walka sesji (turniej)
  final int step; // ile wymian już pokazano (0 = start)
  final bool done; // bieżąca walka dograna do końca
  final bool finished; // cała sesja zakończona → ekran nagród
  FightState copy({int? bout, int? step, bool? done, bool? finished}) =>
      FightState(bout: bout ?? this.bout, step: step ?? this.step, done: done ?? this.done, finished: finished ?? this.finished);
}

class FightController extends StateNotifier<FightState> {
  FightController(this._ref, this.session) : super(const FightState()) {
    _schedule();
  }
  final Ref _ref;
  final FightSession session;
  Timer? _t;

  FightReport get report => session.reports[state.bout];

  /// Hak pod Rive: tu można podpiąć wyzwalacze animacji (akcja/reakcja/wynik) dla bieżącej wymiany.
  void Function(Exchange e)? onExchange;

  void _schedule() {
    _t?.cancel();
    final speed = _ref.read(fightSpeedProvider);
    if (speed == 0) return skipAll();
    _t = Timer(Duration(milliseconds: (1100 / speed).round()), _next);
  }

  void _next() {
    if (!mounted) return;
    final n = report.exchanges.length;
    if (state.step < n) {
      state = state.copy(step: state.step + 1);
      onExchange?.call(report.exchanges[state.step - 1]);
      if (state.step < n) return _schedule();
    }
    state = state.copy(done: true);
    // turniej: krótka pauza i następna walka
    if (state.bout < session.reports.length - 1) {
      _t = Timer(Duration(milliseconds: (1600 / _ref.read(fightSpeedProvider).clamp(1, 4)).round()), () {
        if (!mounted) return;
        state = FightState(bout: state.bout + 1);
        _schedule();
      });
    } else {
      state = state.copy(finished: true);
    }
  }

  /// Zmiana prędkości w trakcie odtwarzania.
  void setSpeed(int s) {
    _ref.read(fightSpeedProvider.notifier).state = s;
    if (!state.finished) _schedule();
  }

  /// POMIŃ: od razu wynik całej sesji.
  void skipAll() {
    _t?.cancel();
    state = FightState(bout: session.reports.length - 1, step: session.reports.last.exchanges.length, done: true, finished: true);
  }

  /// Powtórka od początku.
  void replay() {
    state = const FightState();
    _schedule();
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }
}

final fightControllerProvider =
    StateNotifierProvider.autoDispose.family<FightController, FightState, FightSession>((ref, s) => FightController(ref, s));
