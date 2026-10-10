import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'district_providers.dart';
import 'district_screen.dart' show showDistrictResult;

class _Frame extends StatelessWidget {
  const _Frame({required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: Text(title, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
          const SizedBox(height: 10),
          ...children,
        ]),
      );
}

// ---------------------------------------------------------------------------
// Buffet w Rezydencji: 3 poziomy posiłków, ulepszenie za gotówkę
// ---------------------------------------------------------------------------
class BuffetSheet extends ConsumerStatefulWidget {
  const BuffetSheet({super.key});
  @override
  ConsumerState<BuffetSheet> createState() => _BuffetSheetState();
}

class _BuffetSheetState extends ConsumerState<BuffetSheet> {
  bool _busy = false;
  int? _meal; // wybrany posiłek do karmienia masowego (domyślnie najlepszy dostępny)
  // posiłki z npc.MEALS: (ikona, nazwa, koszt $, sytość, nastrój)
  static const _meals = [
    ('🥪', 'Zwykłe', 10, 15, 0),
    ('🍝', 'Dobre', 25, 25, 5),
    ('🦞', 'Premium', 60, 40, 15),
  ];
  // koszty z economy.BUFFET_COSTS; wymagana Rezydencja ≥ 2
  static const _tiers = [
    ('🥪', 'Zwykły', 'Podstawowe posiłki dla ekipy.', 1500),
    ('🍝', 'Dobre jedzenie', 'Szybsza regeneracja sytości i nastroju.', 4000),
    ('🦞', 'Premium catering', 'Najlepsze posiłki — ekipa wraca do formy najszybciej.', 10000),
  ];

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(districtProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final lv = d.buffet;
    final res = d.byId('residence').level;
    final next = lv < 3 ? _tiers[lv] : null;
    return _Frame(title: '🍽️ Buffet w Rezydencji', children: [
      for (var i = 0; i < 3; i++)
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: i < lv ? AppColors.success.withValues(alpha: .08) : AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: i < lv ? AppColors.success : AppColors.border),
          ),
          child: Row(children: [
            Text(_tiers[i].$1, style: const TextStyle(fontSize: 26)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Poziom ${i + 1}: ${_tiers[i].$2}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(_tiers[i].$3, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              ]),
            ),
            Text(i < lv ? '✔' : money(_tiers[i].$4),
                style: TextStyle(fontWeight: FontWeight.w800, color: i < lv ? AppColors.success : AppColors.textSecondary)),
          ]),
        ),
      const SizedBox(height: 8),
      if (next == null)
        const Text('Buffet na najwyższym poziomie.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.gold))
      else if (res < 2)
        const Text('Buffet wymaga Rezydencji na poziomie 2.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.warning))
      else
        FilledButton(
          key: const Key('buffet-upgrade'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          onPressed: _busy || d.cash < next.$4
              ? null
              : () async {
                  setState(() => _busy = true);
                  final r = await ref.read(districtActionsProvider).upgradeBuffet();
                  if (!context.mounted) return;
                  setState(() => _busy = false);
                  showDistrictResult(context, r);
                },
          child: Text('Ulepsz do: ${next.$2} (${money(next.$4)})'),
        ),
      const SizedBox(height: 20),
      const Text('KARMIENIE MASOWE', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
      const SizedBox(height: 8),
      if (lv == 0)
        const Text('Najpierw ulepsz Buffet do poziomu 1.', style: TextStyle(color: AppColors.textSecondary))
      else ...[
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (var i = 0; i < 3; i++)
            ChoiceChip(
              key: Key('meal-${i + 1}'),
              selected: (_meal ?? lv) == i + 1,
              onSelected: i < lv ? (_) => setState(() => _meal = i + 1) : null,
              label: Text('${_meals[i].$1} ${_meals[i].$2} ${_meals[i].$3} \$${i < lv ? '' : ' 🔒'}'),
            ),
        ]),
        const SizedBox(height: 6),
        () {
          final m = _meals[(_meal ?? lv) - 1];
          final n = d.npcCount;
          return Text('Sytość +${m.$4}${m.$5 > 0 ? ', nastrój +${m.$5}' : ''} · $n NPC × ${m.$3} \$ = ${money(n * m.$3)}',
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary));
        }(),
        const SizedBox(height: 10),
        FilledButton.icon(
          key: const Key('feed-all'),
          style: FilledButton.styleFrom(backgroundColor: AppColors.success, foregroundColor: Colors.black, minimumSize: const Size.fromHeight(46)),
          icon: const Icon(Icons.restaurant_rounded),
          label: const Text('🍔 KARMIENIE MASOWE', style: TextStyle(fontWeight: FontWeight.w800)),
          onPressed: _busy || d.npcCount == 0
              ? null
              : () async {
                  setState(() => _busy = true);
                  final r = await ref.read(districtActionsProvider).feedAll(_meal ?? lv);
                  if (!context.mounted) return;
                  setState(() => _busy = false);
                  showDistrictResult(context, r);
                },
        ),
      ],
    ]);
  }
}

// ---------------------------------------------------------------------------
// Sala Chwały: statystyki, osiągnięcia, trzystopniowy PRESTIŻOWY RESET
// ---------------------------------------------------------------------------
class HallSheet extends ConsumerStatefulWidget {
  const HallSheet({super.key});
  @override
  ConsumerState<HallSheet> createState() => _HallSheetState();
}

class _HallSheetState extends ConsumerState<HallSheet> {
  int _step = 0; // 0 = widok Sali, 1 = co znika/zostaje, 2 = wpisz tekst, 3 = timer
  Map<String, dynamic>? _info;
  final _text = TextEditingController();
  Timer? _timer;
  int _left = 10;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _timer?.cancel();
    _text.dispose();
    super.dispose();
  }

  String get _confirm => '${_info?['confirmText'] ?? 'RESET POTWIERDZAM'}';

  Future<void> _start() async {
    setState(() { _busy = true; _error = null; });
    final r = await ref.read(districtActionsProvider).resetArm();
    if (!mounted) return;
    setState(() {
      _busy = false;
      if (r.ok) {
        _info = r.data;
        _step = 1;
      } else {
        _error = r.message;
      }
    });
  }

  void _toTimer() {
    // serwer liczy 10 s od kroku 1 — uzbrajamy ponownie, żeby timer w UI zgadzał się z serwerem
    setState(() => _busy = true);
    ref.read(districtActionsProvider).resetArm().then((r) {
      if (!mounted) return;
      if (!r.ok) {
        setState(() { _busy = false; _error = r.message; });
        return;
      }
      final delay = (r.data?['delaySeconds'] as num?)?.toInt() ?? 10;
      setState(() { _busy = false; _step = 3; _left = delay; });
      _timer = Timer.periodic(const Duration(seconds: 1), (t) {
        if (_left <= 1) t.cancel();
        if (mounted) setState(() => _left--);
      });
    });
  }

  Future<void> _execute() async {
    setState(() { _busy = true; _error = null; });
    final r = await ref.read(districtActionsProvider).resetExecute(_text.text.trim());
    if (!mounted) return;
    setState(() => _busy = false);
    if (r.ok) {
      Navigator.pop(context);
      showDistrictResult(context, r);
    } else {
      setState(() => _error = r.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(districtProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    return _Frame(title: _step == 0 ? '🏆 Sala Chwały' : '🏆 Prestiżowy reset · krok ${_step.clamp(1, 3)}/3', children: [
      if (_error != null)
        Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(_error!, style: const TextStyle(color: AppColors.danger))),
      ...switch (_step) {
        0 => _hall(d),
        1 => _whatHappens(),
        2 => _typeConfirm(),
        _ => _countdown(),
      },
    ]);
  }

  List<Widget> _hall(DistrictData d) {
    final ch = d.character;
    Widget stat(String l, String v) => Container(
          width: 150,
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(10)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(l, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            Text(v, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ]),
        );
    return [
      Wrap(spacing: 8, runSpacing: 8, children: [
        stat('Resety na świecie', '${d.resets}'),
        stat('Bonus dochodu', '+${d.prestigeBonus}%'),
        stat('XP', '${d.xp}'),
        stat('Elo', '${ch['rating'] ?? '-'}'),
        stat('Walki W/P/R', '${ch['wins'] ?? 0}/${ch['losses'] ?? 0}/${ch['draws'] ?? 0}'),
        stat('Zebrane ze skarbców', money(d.collected)),
      ]),
      const SizedBox(height: 14),
      const Text('OSIĄGNIĘCIA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
      const SizedBox(height: 6),
      if (d.titles.isEmpty)
        const Text('Brak tytułów — pierwszy reset przyniesie tytuł „Reset #1”.', style: TextStyle(color: AppColors.textSecondary))
      else
        Wrap(spacing: 6, runSpacing: 6, children: [for (final t in d.titles) Chip(label: Text('🎖️ $t'))]),
      const SizedBox(height: 18),
      FilledButton(
        key: const Key('reset-start'),
        style: FilledButton.styleFrom(backgroundColor: AppColors.gold, foregroundColor: Colors.black, minimumSize: const Size.fromHeight(50)),
        onPressed: _busy ? null : _start,
        child: const Text('🏆 PRESTIŻOWY RESET', style: TextStyle(fontWeight: FontWeight.w900)),
      ),
    ];
  }

  List<Widget> _whatHappens() {
    final i = _info ?? const {};
    List<String> l(String k) => [for (final x in (i[k] as List?) ?? const []) '$x'];
    Widget box(String title, Color c, List<String> items) => Container(
          padding: const EdgeInsets.all(12),
          margin: const EdgeInsets.only(bottom: 10),
          decoration: BoxDecoration(color: c.withValues(alpha: .08), borderRadius: BorderRadius.circular(12), border: Border.all(color: c.withValues(alpha: .5))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: TextStyle(fontWeight: FontWeight.w800, color: c)),
            const SizedBox(height: 6),
            for (final x in items) Text('• $x', style: const TextStyle(fontSize: 13)),
          ]),
        );
    return [
      box('❌ ZNIKA', AppColors.danger, l('wipes')),
      box('✅ ZOSTAJE', AppColors.success, [
        '💎 ${i['diamondsToAccount'] ?? 0} diamentów trafi na konto główne',
        ...l('keeps'),
      ]),
      Text('Reset #${i['resetNumber']}: +1 Punkt Prestiżu (razem ${i['prestigeAfter']}), stały bonus dochodu +${i['bonusAfter']}% (max ${i['bonusMax']}%).',
          style: const TextStyle(color: AppColors.gold)),
      const SizedBox(height: 14),
      Row(children: [
        Expanded(child: OutlinedButton(onPressed: () => setState(() => _step = 0), child: const Text('Anuluj'))),
        const SizedBox(width: 10),
        Expanded(child: FilledButton(key: const Key('reset-next1'), onPressed: () => setState(() => _step = 2), child: const Text('Rozumiem, dalej'))),
      ]),
    ];
  }

  List<Widget> _typeConfirm() => [
        Text('Wpisz dokładnie: $_confirm', style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        TextField(
          key: const Key('reset-text'),
          controller: _text,
          autofocus: true,
          textCapitalization: TextCapitalization.characters,
          decoration: InputDecoration(hintText: _confirm),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: OutlinedButton(onPressed: () => setState(() => _step = 1), child: const Text('Wstecz'))),
          const SizedBox(width: 10),
          Expanded(
            child: FilledButton(
              key: const Key('reset-next2'),
              onPressed: _busy || _text.text.trim() != _confirm ? null : _toTimer,
              child: const Text('Dalej'),
            ),
          ),
        ]),
      ];

  List<Widget> _countdown() => [
        const Text('Ostatnia szansa na rezygnację. Reset jest nieodwracalny.', textAlign: TextAlign.center),
        const SizedBox(height: 16),
        FilledButton(
          key: const Key('reset-exec'),
          style: FilledButton.styleFrom(backgroundColor: AppColors.danger, minimumSize: const Size.fromHeight(54)),
          onPressed: _left > 0 || _busy ? null : _execute,
          child: Text(_left > 0 ? 'Wykonaj Reset ($_left s)' : (_busy ? 'Resetuję…' : '🏆 Wykonaj Reset'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
        ),
        const SizedBox(height: 8),
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Rezygnuję')),
      ];
}

// ---------------------------------------------------------------------------
// Garaż: flota — paliwo ⛽, zużycie 🔧, tankowanie, serwis, Automatyczny Mechanik
// ---------------------------------------------------------------------------
class FleetSheet extends ConsumerStatefulWidget {
  const FleetSheet({super.key});
  @override
  ConsumerState<FleetSheet> createState() => _FleetSheetState();
}

class _FleetSheetState extends ConsumerState<FleetSheet> {
  String? _busy;
  bool _salon = false;

  Widget _tabs() => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: SegmentedButton<bool>(
          segments: const [
            ButtonSegment(value: false, icon: Icon(Icons.garage_rounded, size: 18), label: Text('Moje auta')),
            ButtonSegment(value: true, icon: Text('🛒'), label: Text('SALON AUT')),
          ],
          selected: {_salon},
          showSelectedIcon: false,
          onSelectionChanged: (v) => setState(() => _salon = v.first),
        ),
      );

  /// Salon: auta z katalogu GARAGE na sprzedaż (bez „Mistrza Rankingu” — jest z nagród).
  List<Widget> _salonList(DistrictData d, DistrictActions a) {
    final lvl = (1 + math.sqrt(1 + 8 * d.xp / 100)) ~/ 2;
    final owned = {for (final c in d.fleet) c.id};
    final cars = [
      for (final g in ((d.catalog['vehicles'] as List?) ?? const []).whereType<Map>())
        if (g['buyable'] != false && g['bonus'] != true) g.cast<String, dynamic>()
    ]..sort((x, y) => (x['price'] as num).compareTo(y['price'] as num));
    return [
      Text('Gotówka: ${money(d.cash)} · Twój poziom: $lvl · miejsca w garażu zależą od Rezydencji',
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      const SizedBox(height: 10),
      for (final g in cars) _carOffer(g, lvl, owned.contains(g['id']), d, a),
    ];
  }

  Widget _carOffer(Map<String, dynamic> g, int lvl, bool owned, DistrictData d, DistrictActions a) {
    final price = (g['price'] as num).toDouble();
    final req = (g['level'] as num).toInt();
    final locked = lvl < req;
    final poor = d.cash < price;
    final icon = switch ('${g['id']}') { 'sedan' => '🚗', 'suv' => '🚙', 'van' => '🚐', _ => '🚚' };
    return Container(
      key: Key('salon-${g['id']}'),
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: owned ? AppColors.success.withValues(alpha: 0.6) : AppColors.border),
      ),
      child: Row(children: [
        Text(icon, style: const TextStyle(fontSize: 30)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${g['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 2),
            Text('${g['description'] ?? ''}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            const SizedBox(height: 4),
            Wrap(spacing: 10, children: [
              Text('⏱️ −${g['discount']}% czasu podróży', style: const TextStyle(fontSize: 11, color: AppColors.primary)),
              Text('⛽ ${g['fuel']}%/przystanek', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              Text('🔧 serwis ${money((g['service'] as num).toDouble())}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              Text('lvl $req', style: TextStyle(fontSize: 11, color: locked ? AppColors.danger : AppColors.textSecondary)),
            ]),
          ]),
        ),
        const SizedBox(width: 10),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text(money(price), style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.gold)),
          const SizedBox(height: 6),
          owned
              ? const Chip(label: Text('W garażu', style: TextStyle(fontSize: 11)), visualDensity: VisualDensity.compact)
              : FilledButton(
                  key: Key('buy-${g['id']}'),
                  onPressed: _busy != null || locked || poor ? null : () => _go('buy-${g['id']}', a.buyVehicle('${g['id']}')),
                  child: _busy == 'buy-${g['id']}'
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(locked ? 'lvl $req' : (poor ? 'Za mało \$' : 'Kup')),
                ),
        ]),
      ]),
    );
  }

  Future<void> _go(String key, Future<DistrictResult> f) async {
    setState(() => _busy = key);
    final r = await f;
    if (!mounted) return;
    setState(() => _busy = null);
    showDistrictResult(context, r);
  }

  static Color _fuelColor(double f) => f > 50 ? AppColors.success : (f >= 30 ? AppColors.warning : AppColors.danger);
  static Color _wearColor(double w) => w < 30 ? AppColors.success : (w < 60 ? AppColors.warning : AppColors.danger);

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(districtProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final a = ref.read(districtActionsProvider);
    final fleet = d.fleet;
    final worn = fleet.where((c) => c.wear > 0).length;
    final mech = d.vip ? 1000 : 2000;
    if (_salon) return _Frame(title: '🛒 Salon aut', children: [_tabs(), ..._salonList(d, a)]);
    return _Frame(title: '🚗 Flota w Garażu (${fleet.length}/5)', children: [
      _tabs(),
      if (fleet.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 20),
          child: Text('Garaż jest pusty. Kup pierwsze auto w zakładce 🛒 SALON AUT powyżej.',
              textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary)),
        ),
      for (final c in fleet)
        Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: c.active ? AppColors.primary : AppColors.border),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Text(c.icon, style: const TextStyle(fontSize: 24)),
              const SizedBox(width: 10),
              Expanded(child: Text(c.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15))),
              if (c.active)
                const Chip(label: Text('Twoje auto', style: TextStyle(fontSize: 11)), visualDensity: VisualDensity.compact)
              else
                TextButton(onPressed: _busy != null ? null : () => _go('eq-${c.id}', a.equip(c.id)), child: const Text('Jedź tym')),
            ]),
            const SizedBox(height: 8),
            MeterBar(value: c.fuel / 100, color: _fuelColor(c.fuel), height: 7, label: '⛽ Paliwo ${c.fuel.round()}% · ${c.fuelPerHop}% na przystanek'),
            const SizedBox(height: 8),
            MeterBar(value: c.wear / 100, color: _wearColor(c.wear), height: 7, label: '🔧 Zużycie ${c.wear.round()}%'),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: OutlinedButton(
                  key: Key('refuel-${c.id}'),
                  onPressed: _busy != null || c.fuel >= 100 ? null : () => _go('f-${c.id}', a.refuel(c.id)),
                  child: FittedBox(child: Text(c.fuel >= 100 ? 'Bak pełny' : 'Zatankuj do pełna (${money(c.refuelCost(d.vip))})')),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton(
                  key: Key('service-${c.id}'),
                  onPressed: _busy != null || c.wear <= 0 ? null : () => _go('s-${c.id}', a.service(c.id)),
                  child: FittedBox(child: Text(c.wear <= 0 ? 'Sprawne' : 'Serwisuj (${money(c.service)})')),
                ),
              ),
            ]),
          ]),
        ),
      if (fleet.isNotEmpty) ...[
        const SizedBox(height: 6),
        FilledButton.icon(
          key: const Key('auto-mechanic'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          icon: const Icon(Icons.build_circle_rounded),
          onPressed: _busy != null || worn == 0 || d.cash < mech ? null : () => _go('mech', a.autoMechanic()),
          label: Text(worn == 0 ? 'Wszystkie auta sprawne' : 'Automatyczny Mechanik — $worn aut (${money(mech)})'),
        ),
      ],
    ]);
  }
}
