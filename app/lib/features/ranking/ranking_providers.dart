import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../world/world_providers.dart';

/// Ranking Świata: GET /api/worlds/{wid}/rankings → pvp · dungeon · prestige · wealth (Top 20 + moja pozycja).

int _i(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;

class RankRow {
  RankRow(Map<String, dynamic> m)
      : id = _i(m['id']),
        place = _i(m['place']),
        nickname = '${m['nickname'] ?? '?'}',
        tag = m['tag']?.toString(),
        level = _i(m['level']),
        cls = m['cls']?.toString(),
        value = _i(m['value']),
        raw = m;
  final int id, place, level, value;
  final String nickname;
  final String? tag, cls;
  final Map<String, dynamic> raw;
}

class RankBoard {
  factory RankBoard(Object? v) {
    final m = v is Map ? v : const {};
    final me = m['me'];
    return RankBoard._(
      ((m['rows'] as List?) ?? const []).whereType<Map>().map((e) => RankRow(e.cast<String, dynamic>())).toList(),
      me is Map ? RankRow(me.cast<String, dynamic>()) : null,
      _i(m['total']),
    );
  }
  RankBoard._(this.rows, this.me, this.total);
  final List<RankRow> rows;
  final RankRow? me;
  final int total;
}

class RankingData {
  RankingData(Map<String, dynamic> r)
      : season = _i(r['season']),
        seasonEndsAt = _i(r['seasonEndsAt']),
        serverTime = _i(r['serverTime']),
        pvp = RankBoard(r['pvp']),
        dungeon = RankBoard(r['dungeon']),
        prestige = RankBoard(r['prestige']),
        wealth = RankBoard(r['wealth']);
  final int season, seasonEndsAt, serverTime;
  final RankBoard pvp, dungeon, prestige, wealth;

  /// Ile pełnych dni do końca miesięcznego sezonu Elo (czas serwera, nie przeglądarki).
  int get daysLeft => ((seasonEndsAt - serverTime) / 86400000).ceil().clamp(0, 31);
}

final rankingProvider = FutureProvider.autoDispose<RankingData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  return RankingData(await ref.watch(apiClientProvider).get('/api/worlds/$wid/rankings'));
});
