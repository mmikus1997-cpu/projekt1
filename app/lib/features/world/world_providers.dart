import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../shared/models/models.dart';
import '../../shared/services/session_store.dart';

/// Wybrany świat (null → ekran wyboru świata). Zapamiętywany w shared_preferences.
class WorldIdController extends StateNotifier<int?> {
  WorldIdController(this._store) : super(_store.worldId);
  final SessionStore _store;
  Future<void> select(int id) async {
    await _store.saveWorld(id);
    state = id;
  }

  void clear() => state = null;
}

final worldIdProvider = StateNotifierProvider<WorldIdController, int?>(
  (ref) => WorldIdController(ref.watch(sessionStoreProvider)),
);

final worldsProvider = FutureProvider.autoDispose<List<WorldInfo>>((ref) async {
  final r = await ref.watch(apiClientProvider).get('/api/worlds');
  return ((r['worlds'] as List?) ?? const []).whereType<Map>().map((m) => WorldInfo.fromJson(m.cast())).toList();
});
