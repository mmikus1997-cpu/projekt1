import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../dashboard/dashboard_providers.dart';
import '../world/world_providers.dart';
import 'club_providers.dart';
import 'stat_breakdown.dart';

/// Ekwipunek i Sklep Klubowy (Etap 7 GDD v3.1): GET /gear, GET /gear/shop + akcje equip/unequip/craft/buy.

int _i(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;

/// Kolory tierów T1–T4 (grey/green/blue/purple z backendu).
Color tierColor(Object? c) => switch ('$c') {
      'green' => const Color(0xFF4ADE80),
      'blue' => const Color(0xFF4AA8FF),
      'purple' => const Color(0xFFB57BFF),
      _ => const Color(0xFF9CA3AF),
    };

const slotIcons = {
  'gloves': '🥊',
  'shoes': '👟',
  'pants': '👖',
  'belt': '🎗️',
  'shirt': '👕',
  'head': '🧣',
  'amulet': '📿',
  'ring': '💍',
};

class GearItem {
  GearItem(this.raw);
  final Map<String, dynamic> raw;
  String get id => '${raw['id']}';
  String get name => '${raw['name'] ?? raw['id']}';
  String get slot => '${raw['slot'] ?? ''}';
  int get tier => _i(raw['tier']);
  // widełki ceny sprzedaży (backend losuje kwotę z tego zakresu)
  int get sellMin => _i((raw['sell'] as Map?)?['min']);
  int get sellMax => _i((raw['sell'] as Map?)?['max']);
  Color get color => tierColor(raw['color']);
  bool get legacy => raw['legacy'] == true;
  List<int> get bonus => [for (final v in (raw['bonus'] as List?) ?? const []) _i(v)];
  bool get unique => raw['unique'] == true;
  bool get equipped => raw['equipped'] == true;
  /// QA 4: Rękawice = Broń — zakres obrażeń z backendu (Combat 3.0).
  bool get isWeapon => raw['dmgMin'] != null;
  String get dmgText => '⚔️ Obrażenia: ${_i(raw['dmgMin'])} - ${_i(raw['dmgMax'])}';
}

class GearSlot {
  GearSlot(this.raw);
  final Map<String, dynamic> raw;
  String get slot => '${raw['slot']}';
  String get label => '${raw['label']}';
  GearItem? get item => raw['item'] is Map ? GearItem((raw['item'] as Map).cast<String, dynamic>()) : null;
  String? get legacy => raw['legacy'] as String?;
  String? get mode => raw['mode'] as String?;
}

class GearData {
  GearData(this.raw);
  final Map<String, dynamic> raw;
  List<GearSlot> get slots => [for (final s in (raw['slots'] as List?) ?? const []) GearSlot((s as Map).cast<String, dynamic>())];
  List<GearItem> get uniques => [for (final s in (raw['uniques'] as List?) ?? const []) GearItem((s as Map).cast<String, dynamic>())];
  String get fistsText => '⚔️ Gołe pięści: ${_i((raw['fists'] as Map?)?['dmgMin'] ?? 15)} - ${_i((raw['fists'] as Map?)?['dmgMax'] ?? 25)}';
  List<GearItem> get backpack => [for (final s in (raw['backpack'] as List?) ?? const []) GearItem((s as Map).cast<String, dynamic>())];
  int get capacity => _i(raw['capacity']);
  int get maxCapacity => _i(raw['maxCapacity']);
  List<StatPart> get statBreakdown => parseBreakdown(raw['statBreakdown']);
  List<int> get gearBonus => [for (final v in (raw['gearBonus'] as List?) ?? const []) _i(v)];
  List<String> get fullSets => [for (final v in (raw['fullSets'] as List?) ?? const []) '$v'];
  Map<String, int> get coupons => ((raw['coupons'] as Map?) ?? const {}).map((k, v) => MapEntry('$k', _i(v)));
  int get diamonds => _i(raw['diamonds']);
  num get cash => (raw['cash'] as num?) ?? 0;
}

class ShopOffer {
  ShopOffer(this.raw);
  final Map<String, dynamic> raw;
  int get offer => _i(raw['offer']);
  int get zone => _i(raw['zone']);
  bool get sold => raw['sold'] == true;
  int get level => _i(raw['level']);
  int get cash => _i((raw['price'] as Map?)?['cash']);
  int get dia => _i((raw['price'] as Map?)?['diamonds']);
  int? get altCash => raw['alt'] is Map ? _i((raw['alt'] as Map)['cash']) : null;
  int? get altDia => raw['alt'] is Map ? _i((raw['alt'] as Map)['diamonds']) : null;
  GearItem get item => GearItem(raw);
  // kupon wylosowany w miejscu przedmiotu (kind = coupon)
  bool get isCoupon => raw['kind'] == 'coupon';
  String get coupon => '${raw['coupon'] ?? ''}';
  String get couponName => '${raw['name'] ?? 'Kupon'}';
  int get owned => _i(raw['owned']);
}

class ShopData {
  ShopData(this.raw);
  final Map<String, dynamic> raw;
  String get name => '${raw['name'] ?? 'Sklep Klubowy'}';
  String zoneName(int z) => '${((raw['zones'] as Map?) ?? const {})['$z'] ?? (z == 1 ? 'Pancerz' : 'Biżuteria')}';
  List<ShopOffer> get items => [for (final s in (raw['items'] as List?) ?? const []) ShopOffer((s as Map).cast<String, dynamic>())];
  List<Map<String, dynamic>> get coupons => [for (final s in (raw['coupons'] as List?) ?? const []) (s as Map).cast<String, dynamic>()];
  int get resetAt => _i(raw['resetAt']);
  int get capacity => _i(raw['capacity']);
  int get used => _i(raw['used']);
  int get refreshCost => _i(raw['refreshCost']);
  int get refreshes => _i(raw['refreshes']);
}

final gearProvider = FutureProvider.autoDispose<GearData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  return GearData(await ref.watch(apiClientProvider).get('/api/worlds/$wid/gear'));
});

final shopProvider = FutureProvider.autoDispose<ShopData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) throw StateError('no-world');
  return ShopData(await ref.watch(apiClientProvider).get('/api/worlds/$wid/gear/shop'));
});

/// Akcje ekwipunku i sklepu. Każda odświeża ekwipunek, sklep, klub i HUD (kasa / 💎).
class GearActions {
  GearActions(this._ref);
  final Ref _ref;
  String get _base => '/api/worlds/${_ref.read(worldIdProvider)}/gear';
  ApiClient get _api => _ref.read(apiClientProvider);

  Future<ClubResult> _run(String path, Map<String, dynamic> body) async {
    try {
      final r = await _api.post('$_base$path', body);
      return ClubResult('${r['message'] ?? 'OK'}');
    } on ApiException catch (e) {
      return ClubResult(e.message, ok: false);
    } finally {
      _ref.invalidate(gearProvider);
      _ref.invalidate(shopProvider);
      _ref.invalidate(clubProvider);
      _ref.invalidate(dashboardProvider);
    }
  }

  Future<ClubResult> equip(String item, {String? mode}) => _run('/equip', {'item': item, 'mode': ?mode});
  Future<ClubResult> unequip(String slot) => _run('/unequip', {'slot': slot});
  Future<ClubResult> craft(List<String> items) => _run('/craft', {'items': items});
  Future<ClubResult> buy(int offer, {String pay = 'cash'}) => _run('/shop/buy', {'offer': offer, 'pay': pay});
  Future<ClubResult> buyCoupon(String type, {String pay = 'cash'}) => _run('/shop/buy', {'coupon': type, 'pay': pay});
  /// Nowe losowanie oferty za gotówkę (refreshCost $, bez limitu).
  Future<ClubResult> refreshShop() => _run('/shop/refresh', {});
  Future<ClubResult> sell(String item) => _run('/sell', {'item': item});
  Future<ClubResult> unlockBag(String currency) => _run('/bag/unlock', {'currency': currency});
}

final gearActionsProvider = Provider<GearActions>((ref) => GearActions(ref));
