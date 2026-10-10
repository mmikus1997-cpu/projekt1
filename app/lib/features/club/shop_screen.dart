import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart';
import 'club_providers.dart';
import 'gear_providers.dart';
import 'gear_screen.dart' show bonusText;

/// „Sklep Klubowy”: oferta rotowana co 6 h w 2 strefach (Pancerz, Biżuteria i Broń) + kupony (stałe produkty, 0% losowości).
class ShopScreen extends ConsumerStatefulWidget {
  const ShopScreen({super.key, this.embedded = false});
  /// Etap 1 UI v2: osadzony w hubie „Sklep & EQ” — bez własnego AppBara.
  final bool embedded;
  @override
  ConsumerState<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends ConsumerState<ShopScreen> {
  String? _busy;
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(seconds: 30), (_) => mounted ? setState(() {}) : null);
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _do(String key, Future<ClubResult> f) async {
    setState(() => _busy = key);
    final r = await f;
    if (!mounted) return;
    setState(() => _busy = null);
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(r.message), backgroundColor: r.ok ? AppColors.success : AppColors.danger));
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(shopProvider);
    final club = ref.watch(clubProvider).valueOrNull;
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: widget.embedded ? null : AppBar(
        backgroundColor: AppColors.surface,
        title: const Text('🛍️ Sklep Klubowy', style: TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.all(16), child: ErrorBanner('$e')),
            FilledButton(onPressed: () => ref.invalidate(shopProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
        data: (s) {
          final left = Duration(milliseconds: (s.resetAt - DateTime.now().millisecondsSinceEpoch).clamp(0, 365 * 24 * 3600 * 1000));
          final level = club?.level ?? 0;
          final cash = club?.cash ?? 0;
          final dia = ((club?.s['diamonds']) as num?)?.toInt() ?? 0;
          return RefreshIndicator(
            onRefresh: () => ref.refresh(shopProvider.future),
            child: LayoutBuilder(builder: (context, c) {
              // kompaktowe kafelki: ok. 200 px szerokości, stała wysokość (2 kolumny już od 360 px)
              // stałe 4 kolumny (2 na telefonie): pancerz 8 = 2 pełne rzędy, biżuteria/broń 4 = 1 pełny rząd
              final grid = SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: c.maxWidth >= 640 ? 4 : 2, mainAxisExtent: 160, mainAxisSpacing: 8, crossAxisSpacing: 8);
              return ListView(padding: const EdgeInsets.all(16), children: [
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 980),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      Wrap(spacing: 14, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                        Text(s.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                        Text('🔄 nowa oferta za ${left.inHours} h ${left.inMinutes % 60} min',
                            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        Text('🎒 plecak ${s.used}/${s.capacity}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        Text('💵 ${money(cash)} · 💎 $dia', style: const TextStyle(fontSize: 12, color: AppColors.gold)),
                        OutlinedButton.icon(
                          key: const Key('shop-refresh'),
                          style: OutlinedButton.styleFrom(visualDensity: VisualDensity.compact, foregroundColor: AppColors.gold),
                          onPressed: cash < s.refreshCost || _busy != null ? null : () => _do('refresh', ref.read(gearActionsProvider).refreshShop()),
                          icon: _busy == 'refresh'
                              ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.refresh, size: 16),
                          label: Text('Odśwież · ${money(s.refreshCost)}'),
                        ),
                      ]),
                      const SizedBox(height: 4),
                      const Text('Widzisz, co kupujesz: przedmioty i kupony za stałą cenę. Czasem w ofercie trafi się kupon 🎟️.',
                          style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      for (final z in [1, 2]) ...[
                        const SizedBox(height: 18),
                        Text(z == 1 ? '🛡️ ${s.zoneName(1)}' : '💍 ${s.zoneName(2)}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 10),
                        GridView(
                          gridDelegate: grid,
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          children: [
                            for (final o in s.items.where((o) => o.zone == z))
                              o.isCoupon ? _couponOffer(o, cash, dia) : _offer(o, level, cash, dia, s.used >= s.capacity),
                          ],
                        ),
                      ],
                    ]),
                  ),
                ),
              ]);
            }),
          );
        },
      ),
    );
  }

  Widget _offer(ShopOffer o, int level, double cash, int dia, bool bagFull) {
    final it = o.item;
    final locked = level < o.level;
    final canCash = cash >= o.cash && dia >= o.dia;
    final canAlt = o.altCash != null && cash >= o.altCash! && dia >= o.altDia!;
    final why = o.sold ? 'Sprzedane' : (locked ? 'lvl ${o.level}' : (bagFull ? 'Plecak pełny' : null));
    return Container(
      key: Key('offer-${o.offer}'),
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: o.sold ? AppColors.border : it.color.withValues(alpha: 0.8), width: o.sold ? 1 : 1.5),
      ),
      child: Opacity(
        opacity: o.sold ? 0.45 : 1,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(slotIcons[it.slot] ?? '📦', style: const TextStyle(fontSize: 20)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: it.color.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
              child: Text('T${it.tier}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: it.color)),
            ),
          ]),
          const SizedBox(height: 4),
          Text(it.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: it.color)),
          const SizedBox(height: 2),
          Text(bonusText(it.bonus), maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
          Text('wymaga lvl ${o.level}', style: TextStyle(fontSize: 11, color: locked ? AppColors.danger : AppColors.textSecondary)),
          const Spacer(),
          Row(children: [
            Expanded(
              flex: 3,
              child: FilledButton(
                key: Key('buy-offer-${o.offer}'),
                style: FilledButton.styleFrom(visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 6)),
                onPressed: why != null || !canCash || _busy != null ? null : () => _do('o${o.offer}', ref.read(gearActionsProvider).buy(o.offer)),
                child: _busy == 'o${o.offer}'
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : FittedBox(child: Text(why ?? 'Kup · ${money(o.cash)}${o.dia > 0 ? ' + ${o.dia} 💎' : ''}')),
              ),
            ),
            // alternatywna cena ($ + 💎) obok, nie pod spodem
            if (o.altCash != null && why == null) ...[
              const SizedBox(width: 4),
              Expanded(
                flex: 2,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 4)),
                  onPressed: !canAlt || _busy != null ? null : () => _do('a${o.offer}', ref.read(gearActionsProvider).buy(o.offer, pay: 'mixed')),
                  child: FittedBox(child: Text('${money(o.altCash!)} + ${o.altDia}💎')),
                ),
              ),
            ],
          ]),
        ]),
      ),
    );
  }

  /// Kupon wylosowany w ofercie (zamiast przedmiotu) — za $ albo 💎, jedna sztuka na ofertę.
  Widget _couponOffer(ShopOffer o, double cash, int dia) {
    const gold = AppColors.gold;
    final desc = switch (o.coupon) {
      'xp' => '×2 XP z akcji przez 1 h',
      'instant' => 'Kończy od razu kontrakt lub trening',
      _ => 'Następny kontrakt +10% \$ i XP',
    };
    final busy = _busy != null;
    final s = ButtonStyle(visualDensity: VisualDensity.compact, padding: WidgetStateProperty.all(const EdgeInsets.symmetric(horizontal: 6)));
    return Container(
      key: Key('offer-${o.offer}'),
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        gradient: o.sold ? null : LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [gold.withValues(alpha: .14), AppColors.surface]),
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: o.sold ? AppColors.border : gold.withValues(alpha: .8), width: o.sold ? 1 : 1.5),
      ),
      child: Opacity(
        opacity: o.sold ? 0.45 : 1,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Text('🎟️', style: TextStyle(fontSize: 20)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: gold.withValues(alpha: .18), borderRadius: BorderRadius.circular(20)),
              child: const Text('KUPON', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: gold)),
            ),
          ]),
          const SizedBox(height: 4),
          Text(o.couponName, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: gold)),
          Text(desc, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11)),
          Text('masz: ${o.owned}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          const Spacer(),
          if (o.sold)
            const FilledButton(onPressed: null, child: Text('Sprzedane'))
          else
            Row(children: [
              Expanded(
                child: FilledButton(
                  key: Key('buy-offer-${o.offer}'),
                  style: s,
                  onPressed: cash < o.cash || busy ? null : () => _do('o${o.offer}', ref.read(gearActionsProvider).buy(o.offer)),
                  child: _busy == 'o${o.offer}'
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                      : FittedBox(child: Text(money(o.cash))),
                ),
              ),
              const SizedBox(width: 4),
              Expanded(
                child: OutlinedButton(
                  style: s,
                  onPressed: dia < o.dia || busy ? null : () => _do('d${o.offer}', ref.read(gearActionsProvider).buy(o.offer, pay: 'diamonds')),
                  child: FittedBox(child: Text('${o.dia} 💎')),
                ),
              ),
            ]),
        ]),
      ),
    );
  }
}
