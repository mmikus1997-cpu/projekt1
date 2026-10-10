import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../shared/models/models.dart';
import '../world/world_providers.dart';

/// Jedno żądanie GET /api/worlds/{wid}/dashboard (Etap 8.6). Odświeżane pollingiem z AppShell.
final dashboardProvider = FutureProvider.autoDispose<DashboardData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final r = await ref.watch(apiClientProvider).get('/api/worlds/$wid/dashboard');
  return DashboardData(r);
});

