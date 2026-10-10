import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';

/// Sojusz (organizacja): GET /community + akcje create/apply/invite-decision/fund/building/invest/leave.

int _i(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
Map<String, dynamic> _m(Object? v) => v is Map ? v.cast<String, dynamic>() : <String, dynamic>{};
List<Map<String, dynamic>> _l(Object? v) => v is List ? v.whereType<Map>().map((e) => e.cast<String, dynamic>()).toList() : [];

/// Wynik akcji pod SnackBar.
class AllyResult {
  const AllyResult(this.message, {this.ok = true});
  final String message;
  final bool ok;
}

class AllyMember {
  AllyMember(Map<String, dynamic> m)
      : id = _i(m['id']),
        nickname = '${m['nickname'] ?? '?'}',
        role = '${m['role'] ?? 'member'}';
  final int id;
  final String nickname, role;
  String get roleLabel => switch (role) { 'leader' => '👑 Lider', 'officer' => '⭐ Oficer', _ => 'Członek' };
  int get roleOrder => switch (role) { 'leader' => 0, 'officer' => 1, _ => 2 };
}

class AllyBuilding {
  AllyBuilding(Map<String, dynamic> m, this.level)
      : id = '${m['id']}',
        name = '${m['name']}',
        icon = '${m['icon'] ?? '🏛️'}',
        pct = _i(m['pct']),
        desc = '${m['desc'] ?? ''}';
  final String id, name, icon, desc;
  final int pct, level;
}

/// Jedna dzielnica-terytorium: suma inwestycji, lider, mój udział.
class Territory {
  Territory(Map<String, dynamic> m, {required this.myOrgId, required this.holderTag})
      : district = '${m['district']}',
        total = _i(m['total']),
        myTotal = _i(m['myTotal']),
        myRank = m['myRank'] == null ? null : _i(m['myRank']),
        leaderTag = m['leader'] is Map ? '${(m['leader'] as Map)['tag']}' : null,
        leaderTotal = m['leader'] is Map ? _i((m['leader'] as Map)['total']) : 0,
        leaderId = m['leader'] is Map ? _i((m['leader'] as Map)['org_id']) : null;
  final String district;
  final int total, myTotal, leaderTotal;
  final int? myRank, leaderId;
  final String? leaderTag, holderTag;
  final int? myOrgId;
  double get myShare => total <= 0 ? 0 : myTotal / total;
  double get leaderShare => total <= 0 ? 0 : leaderTotal / total;
  bool get controlled => holderTag != null;
}

class AllianceData {
  AllianceData(Map<String, dynamic> raw, {required this.buildingsCatalog, required this.allyMax, required this.allyCost, required this.controlShare})
      : org = raw['organization'] == null ? null : _m(raw['organization']),
        members = _l(raw['members']).map(AllyMember.new).toList()..sort((a, b) => a.roleOrder.compareTo(b.roleOrder)),
        organizations = _l(raw['organizations']),
        invitations = _l(raw['invitations']),
        applications = _l(raw['applications']),
        appliedTo = raw['appliedTo'] == null ? null : _i(raw['appliedTo']),
        myRole = raw['myRole']?.toString(),
        isOfficer = raw['isOfficer'] == true,
        myHeld = (raw['myHeld'] as List? ?? const []).map((e) => '$e').toSet(),
        characterId = _i(raw['character_id']),
        influenceRaw = _l(raw['influence']);
  final Map<String, dynamic>? org;
  final List<AllyMember> members;
  final List<Map<String, dynamic>> organizations, invitations, applications, influenceRaw;
  final int? appliedTo;
  final String? myRole;
  final bool isOfficer;
  final Set<String> myHeld;
  final int characterId;
  final List<Map<String, dynamic>> buildingsCatalog;
  final int allyMax;
  final List<int> allyCost;
  final double controlShare;

  bool get inAlliance => org != null;
  int get fund => _i(org?['fund']);
  String get name => '${org?['name'] ?? ''}';
  String get tag => '${org?['tag'] ?? ''}';
  int get prestige => _i(org?['prestige']);
  int get orgId => _i(org?['id']);

  List<AllyBuilding> get buildings {
    final lv = _m(org?['buildings']);
    return buildingsCatalog.map((b) => AllyBuilding(b, _i(lv['${b['id']}']))).toList();
  }

  List<Territory> get territories => influenceRaw
      .map((m) => Territory(m, myOrgId: inAlliance ? orgId : null, holderTag: m['holderSince'] != null && m['leader'] is Map ? '${(m['leader'] as Map)['tag']}' : null))
      .toList();
}

final allianceProvider = FutureProvider.autoDispose<AllianceData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  final api = ref.watch(apiClientProvider);
  final raw = await api.get('/api/worlds/$wid/community');
  // katalog budynków sojuszu, koszty i próg kontroli z /dashboard (catalog) — bez osobnego endpointu
  final d = await ref.watch(dashboardProvider.future);
  final cat = d.catalog;
  return AllianceData(raw,
      buildingsCatalog: _l(cat['allyBuildings']),
      allyMax: _i(cat['allyMax'] ?? 3),
      allyCost: ((cat['allyCost'] as List?) ?? const [2000, 5000, 10000]).map(_i).toList(),
      controlShare: 0.55);
});

class AllianceActions {
  AllianceActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<AllyResult> _run(String path, Map<String, dynamic> body, String okMsg) async {
    try {
      final r = await _api.post(path, body);
      return AllyResult('${r['message'] ?? okMsg}');
    } on ApiException catch (e) {
      return AllyResult(e.message, ok: false);
    } finally {
      _ref.invalidate(allianceProvider);
      _ref.invalidate(dashboardProvider);
    }
  }

  Future<AllyResult> create(String name, String tag, String desc) =>
      _run('$_base/organizations', {'name': name, 'tag': tag, 'description': desc}, 'Sojusz [$tag] założony — jesteś Liderem!');
  Future<AllyResult> apply(int orgId, String text) => _run('$_base/organizations/apply', {'org_id': orgId, 'text': text}, 'Podanie wysłane — czekaj na decyzję Lidera.');
  Future<AllyResult> invite(int inviteId, bool accept) =>
      _run('/api/organization-invites/$inviteId/${accept ? 'accept' : 'decline'}', {}, accept ? 'Dołączyłeś do sojuszu!' : 'Zaproszenie odrzucone.');
  Future<AllyResult> application(int appId, bool accept) =>
      _run('/api/org-applications/$appId/${accept ? 'accept' : 'decline'}', {}, accept ? 'Nowy członek przyjęty.' : 'Podanie odrzucone.');
  Future<AllyResult> fund(int amount) => _run('$_base/organizations/fund', {'amount': amount}, 'Wpłacono $amount \$ do Skarbca sojuszu.');
  Future<AllyResult> build(String id) => _run('$_base/organizations/building', {'building': id}, 'Budynek ulepszony.');
  Future<AllyResult> invest(String district, int amount) =>
      _run('$_base/organizations/invest', {'district': district, 'amount': amount}, 'Zainwestowano $amount \$ w dzielnicę $district.');
  Future<AllyResult> role(int targetId, String role) => _run('$_base/organizations/role', {'target_id': targetId, 'role': role}, 'Rola zmieniona.');
  Future<AllyResult> leave() => _run('$_base/organizations/leave', {}, 'Opuściłeś sojusz.');
}

final allianceActionsProvider = Provider<AllianceActions>((ref) => AllianceActions(ref));
