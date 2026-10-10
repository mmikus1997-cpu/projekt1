import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart';
import 'club_models.dart';
import 'club_providers.dart';
import 'gear_providers.dart';
import 'stat_breakdown.dart';

/// „Mój Ekwipunek”: 8 slotów postaci, plecak (inwentarz) i Warsztat (crafting 3 → 1).
class GearScreen extends ConsumerWidget {
  const GearScreen({super.key, this.embedded = false});
  /// Etap 1 UI v2: osadzony w hubie „Sklep & EQ” — sam pasek zakładek, bez tytułu.
  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(gearProvider);
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: AppColors.background,
        appBar: AppBar(
          backgroundColor: AppColors.surface,
          toolbarHeight: embedded ? 0 : kToolbarHeight,
          automaticallyImplyLeading: !embedded,
          title: embedded ? null : const Text('🎒 Mój Ekwipunek', style: TextStyle(fontWeight: FontWeight.w800)),
          bottom: const TabBar(
            labelColor: AppColors.primary,
            indicatorColor: AppColors.primary,
            unselectedLabelColor: AppColors.textSecondary,
            tabs: [
              Tab(key: Key('tab-gear'), icon: Icon(Icons.backpack_rounded, size: 20), text: 'Ekwipunek'),
              Tab(key: Key('tab-craft'), icon: Icon(Icons.handyman_rounded, size: 20), text: 'Warsztat / Crafting'),
            ],
          ),
        ),
        body: async.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Padding(padding: const EdgeInsets.all(16), child: ErrorBanner('$e')),
              FilledButton(onPressed: () => ref.invalidate(gearProvider), child: const Text('Spróbuj ponownie')),
            ]),
          ),
          data: (g) => TabBarView(children: [_GearTab(g: g), _CraftTab(g: g)]),
        ),
      ),
    );
  }
}

void _toast(BuildContext context, ClubResult r) => ScaffoldMessenger.of(context)
    .showSnackBar(SnackBar(content: Text(r.message), backgroundColor: r.ok ? AppColors.success : AppColors.danger));

/// Wycentrowana kolumna o maks. szerokości 1000 px (desktop) — mobile na całą szerokość.
class _Page extends StatelessWidget {
  const _Page({required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1000),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
            ),
          ),
        ],
      );
}

/// Bonus statystyk przedmiotu, np. „💪+4 🧠+3”.
String bonusText(List<int> b) {
  final parts = [for (var i = 0; i < b.length && i < 5; i++) if (b[i] != 0) '${statIcons[i]}+${b[i]}'];
  return parts.isEmpty ? 'bez bonusu' : parts.join('  ');
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text, {this.trailing});
  final String text;
  final String? trailing;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 10),
        child: Row(children: [
          Expanded(
            child: Text(text.toUpperCase(),
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          ),
          if (trailing != null) Text(trailing!, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ]),
      );
}

// ---------------------------------------------------------------------------
// Zakładka 1: sloty + plecak
// ---------------------------------------------------------------------------
class _GearTab extends ConsumerStatefulWidget {
  const _GearTab({required this.g});
  final GearData g;
  @override
  ConsumerState<_GearTab> createState() => _GearTabState();
}

class _GearTabState extends ConsumerState<_GearTab> {
  bool _busy = false;

  Future<void> _do(Future<ClubResult> f) async {
    setState(() => _busy = true);
    final r = await f;
    if (!mounted) return;
    setState(() => _busy = false);
    _toast(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.g;
    final a = ref.read(gearActionsProvider);
    return LayoutBuilder(builder: (context, c) {
      // kompaktowe siatki: sloty ~150 px, plecak ~104 px (więcej kafelków w rzędzie, też na telefonie)
      final narrow = c.maxWidth < 420;
      final slotGrid = SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: narrow ? 130 : 150, mainAxisExtent: 104, mainAxisSpacing: 8, crossAxisSpacing: 8);
      final bagGrid = SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: narrow ? 92 : 104, mainAxisExtent: 92, mainAxisSpacing: 8, crossAxisSpacing: 8);
      // unikaty z Lochu w plecaku (nie zajmują miejsca); założone widać w slotach
      final uniqueIds = {for (final u in g.uniques) u.id};
      final bag = g.backpack.where((it) => !uniqueIds.contains(it.id)).toList();
      final freeUniques = g.uniques.where((u) => !u.equipped).toList();
      return _Page(children: [
        // łączne statystyki z rozbiciem (trening + ekwipunek + unikaty + inne) w dymku
        StatSummary(
          parts: g.statBreakdown,
          footer: g.fullSets.isEmpty ? null : Text('✨ Komplet: ${g.fullSets.join(', ')} (+30%)', style: const TextStyle(fontSize: 12, color: AppColors.gold)),
        ),
        const SizedBox(height: 12),
        const _SectionTitle('Postać — sloty'),
        GridView(
          gridDelegate: slotGrid,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [for (final s in g.slots) _slotCard(s, a)],
        ),
        const SizedBox(height: 16),
        _SectionTitle('Plecak (inwentarz)', trailing: '${bag.length}/${g.capacity} miejsc${freeUniques.isEmpty ? '' : ' · 🏆 ${freeUniques.length} unikat(y) poza limitem'}'),
        if (bag.isEmpty && freeUniques.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppColors.border)),
            child: const Text('Plecak jest pusty. Przedmioty zdobędziesz w Lochu albo kupisz w 🛍️ Sklepie Klubowym.',
                textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary)),
          )
        else
          GridView(
            gridDelegate: bagGrid,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              for (final u in freeUniques) _uniqueCard(u, a),
              for (final it in bag) _bagCard(it, a),
              for (var i = bag.length; i < g.capacity; i++)
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppColors.border),
                    color: AppColors.surface.withValues(alpha: 0.4),
                  ),
                ),
            ],
          ),
      ]);
    });
  }

  Widget _slotCard(GearSlot s, GearActions a) {
    final it = s.item;
    final uq = widget.g.uniques.where((u) => u.equipped && u.slot == s.slot).firstOrNull;
    final color = it?.color ?? (uq != null ? AppColors.gold : AppColors.border);
    return InkWell(
      key: Key('slot-${s.slot}'),
      borderRadius: BorderRadius.circular(14),
      onTap: it == null || _busy
          ? null
          : () => _sheet(
                title: it.name,
                color: it.color,
                lines: ['Slot: ${s.label} · T${it.tier}${s.mode != null ? ' · tryb ${s.mode}' : ''}', if (it.isWeapon) it.dmgText, bonusText(it.bonus)],
                action: 'Zdejmij do plecaka',
                onAction: () => _do(a.unequip(s.slot)),
              ),
      child: Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color, width: it != null ? 2 : 1),
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Text(slotIcons[s.slot] ?? '❔', style: TextStyle(fontSize: 20, color: it == null ? Colors.white38 : null)),
          const SizedBox(height: 2),
          Text(s.label, style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)),
          const SizedBox(height: 2),
          Text(
            it != null ? it.name.split(' · ').last : (uq != null ? '🏆 ${uq.name}' : (s.legacy != null ? 'Podstawowe' : 'pusty')),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: it != null ? it.color : (uq != null ? AppColors.gold : AppColors.textSecondary)),
          ),
          if (it != null || uq != null) Text(bonusText((it ?? uq)!.bonus), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10)),
          if (s.slot == 'gloves')
            Text(
              (it ?? uq)?.isWeapon == true ? (it ?? uq)!.dmgText : widget.g.fistsText,
              key: const Key('gloves-dmg'),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AppColors.danger),
            ),
        ]),
      ),
    );
  }

  Widget _bagCard(GearItem it, GearActions a) => InkWell(
        key: Key('bag-${it.id}'),
        borderRadius: BorderRadius.circular(12),
        onTap: _busy || it.legacy
            ? null
            : () => _sheet(
                  title: it.name,
                  color: it.color,
                  lines: ['T${it.tier} · slot: ${it.name.split(' · ').first}', if (it.isWeapon) it.dmgText, bonusText(it.bonus)],
                  compare: _compare(it),
                  action: 'Załóż',
                  onAction: () async {
                    String? mode;
                    if (it.tier == 4) {
                      mode = await _pickMode();
                      if (mode == null) return;
                    }
                    await _do(a.equip(it.id, mode: mode));
                  },
                  secondary: it.sellMax > 0 ? '💰 Sprzedaj · ${money(it.sellMin)}–${money(it.sellMax)}' : null,
                  onSecondary: () async {
                    final ok = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        backgroundColor: AppColors.surface,
                        title: Text('Sprzedać ${it.name}?'),
                        content: Text('Dostaniesz losową kwotę od ${money(it.sellMin)} do ${money(it.sellMax)} (zależnie od tieru i bonusów). Tego nie da się cofnąć.'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
                          FilledButton(key: const Key('sell-confirm'), onPressed: () => Navigator.pop(ctx, true), child: const Text('Sprzedaj')),
                        ],
                      ),
                    );
                    if (ok == true) await _do(a.sell(it.id));
                  },
                ),
        child: Container(
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: it.color.withValues(alpha: 0.8)),
          ),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(slotIcons[it.slot] ?? '📦', style: const TextStyle(fontSize: 20)),
            const SizedBox(height: 2),
            Text(it.name.split(' · ').last,
                maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: it.color)),
            Text('T${it.tier}', style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)),
            if (it.isWeapon) Text(it.dmgText.replaceFirst('Obrażenia: ', ''), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AppColors.danger)),
          ]),
        ),
      );

  /// Unikat z Lochu w plecaku: złota ramka i 🏆; nie zajmuje miejsca w plecaku.
  Widget _uniqueCard(GearItem u, GearActions a) => InkWell(
        key: Key('unique-${u.id}'),
        borderRadius: BorderRadius.circular(10),
        onTap: _busy
            ? null
            : () => _sheet(
                  title: '🏆 ${u.name}',
                  color: AppColors.gold,
                  lines: ['Unikat z bossa Lochu · slot: ${u.slot} · nie zajmuje miejsca w plecaku', if (u.isWeapon) u.dmgText, bonusText(u.bonus)],
                  compare: _compare(u),
                  action: 'Załóż',
                  onAction: () => _do(a.equip(u.id)),
                ),
        child: Container(
          padding: const EdgeInsets.all(5),
          decoration: BoxDecoration(
            color: AppColors.gold.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.gold.withValues(alpha: 0.7), width: 1.5),
          ),
          child: Stack(children: [
            const Positioned(top: 0, right: 0, child: Text('🏆', style: TextStyle(fontSize: 10))),
            Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(slotIcons[u.slot] ?? '🏆', style: const TextStyle(fontSize: 20)),
                const SizedBox(height: 2),
                Text(u.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: AppColors.gold)),
                Text(bonusText(u.bonus), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9)),
                if (u.isWeapon) Text(u.dmgText.replaceFirst('Obrażenia: ', ''), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: AppColors.danger)),
              ]),
            ),
          ]),
        ),
      );

  /// Porównanie z przedmiotem założonym w tym samym slocie (albo „Slot pusty”).
  Widget _compare(GearItem it) {
    final slot = widget.g.slots.where((s) => s.slot == it.slot).firstOrNull;
    final cur = slot?.item ?? widget.g.uniques.where((u) => u.equipped && u.slot == it.slot && u.id != it.id).firstOrNull;
    final rows = <Widget>[];
    Widget row(String label, num now, num next) {
      final d = next - now;
      final c = d > 0 ? AppColors.success : (d < 0 ? AppColors.danger : AppColors.textSecondary);
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
          SizedBox(width: 56, child: Text('$now', textAlign: TextAlign.right, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary))),
          const SizedBox(width: 22, child: Text('→', textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: AppColors.textSecondary))),
          SizedBox(width: 48, child: Text('$next', textAlign: TextAlign.right, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800))),
          SizedBox(width: 52, child: Text(d == 0 ? '=' : '${d > 0 ? '+' : ''}$d', textAlign: TextAlign.right, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: c))),
        ]),
      );
    }
    const names = ['💪 Siła', '🧠 Inteligencja', '⚡ Refleks', '🗣️ Charyzma', '🦊 Spryt'];
    final cb = cur?.bonus ?? const <int>[];
    for (var i = 0; i < 5; i++) {
      final n = i < cb.length ? cb[i] : 0, x = i < it.bonus.length ? it.bonus[i] : 0;
      if (n != 0 || x != 0) rows.add(row(names[i], n, x));
    }
    int dmg(GearItem? g, String k, int fist) => g != null && g.isWeapon ? (g.raw[k] as num).toInt() : fist;
    if (it.isWeapon) {
      final fm = ((widget.g.raw['fists'] as Map?)?['dmgMin'] as num?)?.toInt() ?? 15;
      final fx = ((widget.g.raw['fists'] as Map?)?['dmgMax'] as num?)?.toInt() ?? 25;
      rows.add(row('⚔️ Obrażenia min', dmg(cur, 'dmgMin', fm), dmg(it, 'dmgMin', fm)));
      rows.add(row('⚔️ Obrażenia max', dmg(cur, 'dmgMax', fx), dmg(it, 'dmgMax', fx)));
    }
    return Container(
      key: const Key('gear-compare'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(cur == null ? 'Porównanie · slot pusty (bez przedmiotu)' : 'Porównanie z założonym: ${cur.name}',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: cur?.color ?? AppColors.textSecondary)),
        const SizedBox(height: 6),
        if (rows.isEmpty) const Text('brak różnic', style: TextStyle(fontSize: 13, color: AppColors.textSecondary)) else ...rows,
      ]),
    );
  }

  Future<String?> _pickMode() => showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          backgroundColor: AppColors.surface,
          title: const Text('Tryb przedmiotu T4'),
          content: const Text('A: +5 do wszystkich statystyk\nB: +12 do statystyki klasowej'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, 'A'), child: const Text('Tryb A')),
            FilledButton(onPressed: () => Navigator.pop(ctx, 'B'), child: const Text('Tryb B')),
          ],
        ),
      );

  void _sheet(
          {required String title,
          required Color color,
          required List<String> lines,
          required String action,
          required VoidCallback onAction,
          Widget? compare,
          String? secondary,
          VoidCallback? onSecondary}) =>
      showModalBottomSheet(
        context: context,
        backgroundColor: AppColors.surface,
        builder: (ctx) => SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text(title, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: color)),
              const SizedBox(height: 6),
              for (final l in lines) Text(l, style: const TextStyle(color: AppColors.textSecondary)),
              if (compare != null) ...[const SizedBox(height: 12), compare],
              const SizedBox(height: 16),
              FilledButton(
                key: const Key('gear-action'),
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                onPressed: () {
                  Navigator.pop(ctx);
                  onAction();
                },
                child: Text(action),
              ),
              if (secondary != null && onSecondary != null) ...[
                const SizedBox(height: 8),
                OutlinedButton(
                  key: const Key('gear-sell'),
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(44), foregroundColor: AppColors.gold),
                  onPressed: () {
                    Navigator.pop(ctx);
                    onSecondary();
                  },
                  child: Text(secondary),
                ),
              ],
            ]),
          ),
        ),
      );
}

// ---------------------------------------------------------------------------
// Zakładka 2: Warsztat — 3 przedmioty tego samego tieru → 1 przedmiot tieru wyżej
// ---------------------------------------------------------------------------
class _CraftTab extends ConsumerStatefulWidget {
  const _CraftTab({required this.g});
  final GearData g;
  @override
  ConsumerState<_CraftTab> createState() => _CraftTabState();
}

class _CraftTabState extends ConsumerState<_CraftTab> {
  final List<int> _picked = []; // indeksy w plecaku (mogą być duplikaty id)
  bool _busy = false;

  static const _cost = {1: (500, 0), 2: (2000, 0), 3: (10000, 20)}; // CRAFT_COST (gear.py)

  @override
  Widget build(BuildContext context) {
    final bag = widget.g.backpack.where((i) => !i.legacy).toList();
    final tier = _picked.isEmpty ? null : bag[_picked.first].tier;
    final cost = tier == null ? null : _cost[tier];
    return _Page(children: [
      Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppColors.border)),
        child: const Text(
          '🔨 Połącz 3 przedmioty tego samego tieru w 1 przedmiot tieru wyżej (slot i set losowe).\n'
          'Koszt: T1→T2 500 \$ · T2→T3 2 000 \$ · T3→T4 10 000 \$ + 20 💎. Tier 4 to maksimum.',
          style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
        ),
      ),
      const SizedBox(height: 14),
      // 3 miejsca na składniki
      Row(children: [
        for (var k = 0; k < 3; k++) ...[
          Expanded(
            child: Container(
              height: 96,
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: k < _picked.length ? bag[_picked[k]].color : AppColors.border, width: k < _picked.length ? 2 : 1),
              ),
              child: Center(
                child: k < _picked.length
                    ? Column(mainAxisSize: MainAxisSize.min, children: [
                        Text(slotIcons[bag[_picked[k]].slot] ?? '📦', style: const TextStyle(fontSize: 26)),
                        Text(bag[_picked[k]].name.split(' · ').last, style: TextStyle(fontSize: 12, color: bag[_picked[k]].color)),
                      ])
                    : const Text('+', style: TextStyle(fontSize: 30, color: AppColors.textSecondary)),
              ),
            ),
          ),
          if (k < 2) const Padding(padding: EdgeInsets.symmetric(horizontal: 6), child: Text('+', style: TextStyle(fontSize: 18))),
        ],
      ]),
      const SizedBox(height: 12),
      FilledButton.icon(
        key: const Key('craft-go'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50), backgroundColor: AppColors.gold, foregroundColor: const Color(0xFF1A1300)),
        onPressed: _picked.length != 3 || _busy || tier == 4 ? null : _craft,
        icon: _busy
            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.auto_fix_high_rounded),
        label: Text(_picked.length != 3
            ? 'Wybierz 3 przedmioty (${_picked.length}/3)'
            : tier == 4
                ? 'Tier 4 to maksimum'
                : 'Craftuj T$tier → T${tier! + 1} (${money(cost!.$1)}${cost.$2 > 0 ? ' + ${cost.$2} 💎' : ''})'),
      ),
      const SizedBox(height: 18),
      const _SectionTitle('Wybierz z plecaka'),
      if (bag.isEmpty)
        const Text('Plecak jest pusty — nie ma czego łączyć.', style: TextStyle(color: AppColors.textSecondary))
      else
        Wrap(spacing: 10, runSpacing: 10, children: [
          for (var i = 0; i < bag.length; i++)
            () {
              final it = bag[i];
              final sel = _picked.contains(i);
              final blocked = !sel && (_picked.length >= 3 || (tier != null && it.tier != tier));
              return FilterChip(
                key: Key('craft-pick-$i'),
                selected: sel,
                onSelected: blocked || _busy ? null : (v) => setState(() => v ? _picked.add(i) : _picked.remove(i)),
                avatar: Text(slotIcons[it.slot] ?? '📦'),
                label: Text('${it.name} · T${it.tier}'),
                side: BorderSide(color: it.color.withValues(alpha: 0.7)),
                selectedColor: it.color.withValues(alpha: 0.25),
              );
            }(),
        ]),
    ]);
  }

  Future<void> _craft() async {
    final bag = widget.g.backpack.where((i) => !i.legacy).toList();
    setState(() => _busy = true);
    final r = await ref.read(gearActionsProvider).craft([for (final i in _picked) bag[i].id]);
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r.ok) _picked.clear();
    });
    _toast(context, r);
  }
}
