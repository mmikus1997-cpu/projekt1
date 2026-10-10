import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';

/// Profil gracza (GET /account/profile + /milestones) i Battle Pass (GET /battlepass, POST premium/claim).

int _i(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;

class ProfileData {
  ProfileData(Map<String, dynamic> profile, Map<String, dynamic> milestones, int wid, this.serverNow)
      : username = '${profile['username'] ?? ''}',
        prestigePoints = _i(profile['prestigePoints']),
        activeDays = _i(milestones['activeDays']),
        ch = ((profile['characters'] as List?) ?? const [])
                .whereType<Map>()
                .map((e) => e.cast<String, dynamic>())
                .where((c) => _i(c['worldId']) == wid)
                .firstOrNull ??
            const {};
  final String username;
  final int prestigePoints, activeDays, serverNow;
  final Map<String, dynamic> ch;

  String get nickname => '${ch['nickname'] ?? username}';
  String get world => '${ch['world'] ?? ''}';
  int get level => _i(ch['level']);
  int get xp => _i(ch['xp']);
  int get xpBase => _i(ch['xpBase']);
  int get xpNext => _i(ch['xpNext']);
  int get rating => _i(ch['rating']).round();
  int get wins => _i(ch['wins']);
  int get losses => _i(ch['losses']);
  int get draws => _i(ch['draws']);
  int get resets => _i(ch['resets']);
  String? get cls => ch['clas']?.toString();
  List<String> get frames => ((ch['frames'] as List?) ?? const []).map((e) => '$e').toList();
  List<String> get titles => ((ch['titles'] as List?) ?? const []).map((e) => e is Map ? '${e['label'] ?? e['code']}' : '$e').toList();
  int get createdAt => _i(ch['createdAt']);

  /// Staż: pełne dni od utworzenia postaci na tym świecie.
  int get seniorityDays => createdAt <= 0 ? 0 : ((serverNow - createdAt) / 86400000).floor();
}

class BpReward {
  BpReward(Map<String, dynamic> m)
      : kind = '${m['kind'] ?? ''}',
        amount = _i(m['amount']),
        name = m['name']?.toString(),
        coupon = m['coupon']?.toString(),
        unique = m['unique'] == true,
        claimed = m['claimed'] == true;
  final String kind;
  final int amount;
  final String? name, coupon;
  final bool unique, claimed;

  String get icon => switch (kind) {
        'cash' => '💵',
        'diamonds' => '💎',
        'coupon' => '🎟️',
        'frame' => '🖼️',
        'cosmetic' => '👕',
        'dog' => '🐕',
        'horse' => '🐎',
        _ => '🎁',
      };
  String get label => switch (kind) {
        'cash' => '$amount \$',
        'diamonds' => '$amount💎',
        'coupon' => 'Kupon ${coupon == 'xp' ? 'XP' : coupon == 'instant' ? 'Instant' : coupon ?? ''}${amount > 1 ? ' ×$amount' : ''}',
        _ => name ?? kind,
      };
}

class BpLevel {
  BpLevel(Map<String, dynamic> m)
      : level = _i(m['level']),
        free = BpReward((m['free'] as Map? ?? const {}).cast<String, dynamic>()),
        premium = BpReward((m['premium'] as Map? ?? const {}).cast<String, dynamic>());
  final int level;
  final BpReward free, premium;
}

class BattlePass {
  BattlePass(Map<String, dynamic> r)
      : season = '${r['season'] ?? ''}',
        theme = '${r['theme'] ?? ''}',
        endsAt = _i(r['endsAt']),
        xp = _i(r['xp']),
        level = _i(r['level']),
        xpPerLevel = _i(r['xpPerLevel']) == 0 ? 100 : _i(r['xpPerLevel']),
        levels = _i(r['levels']) == 0 ? 30 : _i(r['levels']),
        premium = r['premium'] == true,
        diamonds = _i(r['diamonds']),
        priceDiamonds = _i((r['price'] as Map?)?['diamonds'] ?? 400),
        xpSources = ((r['xpSources'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', _i(v))),
        tracks = ((r['tracks'] as List?) ?? const []).whereType<Map>().map((e) => BpLevel(e.cast<String, dynamic>())).toList();
  final String season, theme;
  final int endsAt, xp, level, xpPerLevel, levels, diamonds, priceDiamonds;
  final bool premium;
  final Map<String, int> xpSources;
  final List<BpLevel> tracks;

  int get xpInLevel => level >= levels ? xpPerLevel : xp - level * xpPerLevel;
  int get claimable => tracks
      .where((t) => t.level <= level)
      .fold(0, (n, t) => n + (t.free.claimed ? 0 : 1) + (premium && !t.premium.claimed ? 1 : 0));
}

final profileProvider = FutureProvider.autoDispose<ProfileData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final res = await Future.wait([api.get('/api/account/profile'), api.get('/api/worlds/$wid/milestones')]);
  final serverNow = DateTime.now().millisecondsSinceEpoch;
  return ProfileData(res[0], res[1], wid, serverNow);
});

final battlePassProvider = FutureProvider.autoDispose<BattlePass>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  return BattlePass(await ref.watch(apiClientProvider).get('/api/worlds/$wid/battlepass'));
});

class BpResult {
  const BpResult(this.message, {this.ok = true});
  final String message;
  final bool ok;
}

class BattlePassActions {
  BattlePassActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}/battlepass';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<BpResult> _run(String path, Map<String, dynamic> body, String Function(Map<String, dynamic>) okMsg) async {
    try {
      final r = await _api.post('$_base$path', body);
      return BpResult(okMsg(r));
    } on ApiException catch (e) {
      return BpResult(e.message, ok: false);
    } finally {
      _ref.invalidate(battlePassProvider);
      _ref.invalidate(profileProvider);
      _ref.invalidate(dashboardProvider);
    }
  }

  Future<BpResult> buyPremium() => _run('/premium', {}, (_) => '👑 Ścieżka Premium odblokowana na ten sezon!');
  Future<BpResult> claim(int level, String track) => _run('/claim', {'level': level, 'track': track}, (r) {
        final rew = (r['reward'] as Map?)?.cast<String, dynamic>();
        return rew == null ? 'Nagroda odebrana.' : 'Odebrano: ${BpReward(rew).icon} ${BpReward(rew).label}';
      });
}

final battlePassActionsProvider = Provider<BattlePassActions>((ref) => BattlePassActions(ref));
