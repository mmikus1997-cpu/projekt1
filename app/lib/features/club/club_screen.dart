import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart';
import '../crew/crew_sheets.dart' show showCrewModal;
import 'club_models.dart';
import 'club_providers.dart';
import 'fight_screen.dart';
import 'gear_providers.dart' show gearProvider;
import 'stat_breakdown.dart';

/// Sala Klubowa — hub dyscyplin. Siatka kafelków: 2 kolumny mobile, 3 tablet, 4 desktop.
/// Etap 1 UI v2: pod-zakładki Klubu (Trening · Pojedynki · Mini-gry).
final clubCategoryProvider = StateProvider<String>((_) => 'duel');
const clubCategories = [('train', '🏋️ Trening'), ('duel', '⚔️ Pojedynki'), ('mini', '🎯 Mini-gry')];

class ClubHouseScreen extends ConsumerWidget {
  const ClubHouseScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(clubProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(clubProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
      ),
      data: (d) => LayoutBuilder(builder: (context, c) {
        final cols = c.maxWidth >= 1000 ? 4 : (c.maxWidth >= 600 ? 3 : 2);
        final pad = c.maxWidth >= 600 ? 24.0 : 12.0;
        final cat = ref.watch(clubCategoryProvider);
        final tiles = _tiles(d).where((t) => t.cat == cat).toList();
        return RefreshIndicator(
          onRefresh: () => ref.refresh(clubProvider.future),
          child: ListView(padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 70), children: [
            Row(children: [
              const Expanded(child: Text('Sala Klubowa', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800))),
              Text('⚡ ${d.energy.round()}', style: const TextStyle(color: AppColors.warning, fontWeight: FontWeight.w800)),
            ]),
            const SizedBox(height: 4),
            Text(
              d.classType == null ? 'Klasa: jeszcze nie wybrana (wybierzesz przy pierwszym PvP)' : 'Klasa: ${_classLabel(d.classType!)}',
              style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 4),
            _PvpLevelLine(d),
            if (d.canEvolve) ...[
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  key: const Key('evolve-open'),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.gold,
                    foregroundColor: const Color(0xFF1A1300),
                    padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
                    textStyle: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.6),
                  ),
                  onPressed: () => showDialog(context: context, builder: (_) => EvolveDialog(data: d)),
                  icon: const Text('✨', style: TextStyle(fontSize: 18)),
                  label: const Text('EWOLUUJ KLASĘ'),
                ),
              ),
            ],
            const SizedBox(height: 16),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final (id, label) in clubCategories)
                ChoiceChip(
                  key: Key('club-cat-$id'),
                  label: Text(label,
                      style: TextStyle(fontWeight: FontWeight.w800, color: cat == id ? AppColors.primary : AppColors.textSecondary)),
                  showCheckmark: false,
                  side: BorderSide(color: cat == id ? AppColors.primary : AppColors.border),
                  backgroundColor: AppColors.surface,
                  selected: cat == id,
                  selectedColor: AppColors.primary.withValues(alpha: 0.22),
                  onSelected: (_) => ref.read(clubCategoryProvider.notifier).state = id,
                ),
            ]),
            const SizedBox(height: 14),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: cols,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: cols == 2 ? 1.0 : 1.25,
              children: [
                for (final t in tiles)
                  _Tile(
                    key: Key('tile-${t.id}'),
                    t: t,
                    onTap: () => t.page ? context.go('/club/${t.id}') : showCrewModal(context, t.sheet()),
                  ),
              ],
            ),
          ]),
        );
      }),
    );
  }

  List<_TileData> _tiles(ClubData d) => [
        _TileData('duel', 'pvp', '⚔️', 'Pojedynki PvP', '${d.dailyUsed}/${ClubData.dailyLimit} dziś · od lvl 2', d.level < 2, () => const PvpSheet()),
        _TileData('duel', 'boxing', '🥊', 'Boks / MMA', 'Turniej · 30⚡ + 200 \$', d.level < 2, () => const BoxingSheet()),
        _TileData('duel', 'dungeon', '🐉', 'Ring / Loch', 'Normal 8⚡ · Hard 15⚡ · Nightmare 25⚡', d.level < 3, () => const DungeonSheet()),
        _TileData('mini', 'horses', '🏇', 'Jazda konna', 'Konkurs · 15⚡ + 80 \$ · nagroda \$ + XP', false, () => const RidingSheet()),
        _TileData('mini', 'agility', '🐕', 'Agility psów', 'Psiarnia · 10 konkursów / 4 h', false, () => const DogSheet()),
        _TileData('train', 'gym', '🏋️', 'Wyzwania siłowe', 'Natychmiast +1 · 5⚡ + od 50 \$', false, () => const GymSheet()),
        _TileData('mini', 'archery', '🎯', 'Łucznictwo', '3 serie dziennie · +maks. energia', false, () => const SportSheet(kind: 'archery')),
        _TileData('mini', 'swim', '🏊', 'Pływanie', '3 serie dziennie · buff klasy', false, () => const SportSheet(kind: 'swim')),
        // Etap 1 UI v2: „Mój Ekwipunek” przeniesiony do zakładki „Sklep & EQ”.
      ];
}

/// „Poziom PvP: N” + postęp do kolejnego poziomu i wybrane ewolucje.
class _PvpLevelLine extends StatelessWidget {
  const _PvpLevelLine(this.d);
  final ClubData d;
  @override
  Widget build(BuildContext context) {
    final evos = [if (d.evo1 != null) '${d.evo1!['icon']} ${d.evo1!['label']}', if (d.evo2 != null) '${d.evo2!['icon']} ${d.evo2!['label']}'];
    final next = d.nextEvolution;
    return Wrap(spacing: 10, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
      Text('Poziom PvP: ${d.pvpLevel}', key: const Key('pvp-level'),
          style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.primary)),
      if (d.pvpNextAt != null)
        Text('(${d.pvpPoints}/${d.pvpNextAt} pkt — wygrana 3, remis 2, przegrana 1)',
            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
      if (evos.isNotEmpty) Text('Ewolucje: ${evos.join(' · ')}', style: const TextStyle(fontSize: 12, color: AppColors.gold)),
      if (next != null && next['available'] != true && d.classType != null)
        Text('Ewolucja ${next['stage'] == 1 ? 'I' : 'II'} od PvP ${next['reqLevel']}',
            style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
    ]);
  }
}

/// Modal ewolucji: 2 ścieżki dla klasy na bieżącym etapie → POST /pvp/evolve.
class EvolveDialog extends ConsumerStatefulWidget {
  const EvolveDialog({super.key, required this.data});
  final ClubData data;
  @override
  ConsumerState<EvolveDialog> createState() => _EvolveDialogState();
}

class _EvolveDialogState extends ConsumerState<EvolveDialog> {
  String? _pick;
  bool _busy = false;
  String? _error;
  @override
  Widget build(BuildContext context) {
    final next = widget.data.nextEvolution ?? const {};
    final stage = next['stage'] == 2 ? 'II' : 'I';
    final opts = [for (final o in (next['options'] as List?) ?? const []) (o as Map).cast<String, dynamic>()];
    return Dialog(
      backgroundColor: AppColors.surface,
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Row(children: [
              Expanded(child: Text('✨ Ewolucja $stage — wybierz ścieżkę', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
            ]),
            Text('Klasa: ${_classLabel(widget.data.classType ?? '')} · wybór jest jednorazowy.',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            const SizedBox(height: 14),
            for (final o in opts)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  key: Key('evo-${o['code']}'),
                  borderRadius: BorderRadius.circular(14),
                  onTap: _busy ? null : () => setState(() => _pick = '${o['code']}'),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: _pick == o['code'] ? AppColors.gold.withValues(alpha: 0.12) : AppColors.surfaceLight,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: _pick == o['code'] ? AppColors.gold : AppColors.border, width: _pick == o['code'] ? 2 : 1),
                    ),
                    child: Row(children: [
                      Text('${o['icon']}', style: const TextStyle(fontSize: 30)),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${o['label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                          Text('Pasywka: ${o['passive']}', style: const TextStyle(fontSize: 12, color: AppColors.gold)),
                          const SizedBox(height: 2),
                          Text('${o['desc']}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                        ]),
                      ),
                    ]),
                  ),
                ),
              ),
            if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: ErrorBanner(_error!)),
            FilledButton(
              key: const Key('evo-confirm'),
              style: FilledButton.styleFrom(backgroundColor: AppColors.gold, foregroundColor: const Color(0xFF1A1300), minimumSize: const Size.fromHeight(48)),
              onPressed: _pick == null || _busy ? null : _confirm,
              child: _busy
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Ewoluuj', style: TextStyle(fontWeight: FontWeight.w900)),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _confirm() async {
    setState(() { _busy = true; _error = null; });
    final r = await ref.read(clubActionsProvider).evolve(_pick!);
    if (!mounted) return;
    if (!r.ok) {
      setState(() { _busy = false; _error = r.message; });
      return;
    }
    final messenger = ScaffoldMessenger.of(context);
    Navigator.pop(context);
    messenger.showSnackBar(SnackBar(content: Text(r.message), backgroundColor: AppColors.success));
  }
}

String _classLabel(String c) => switch (c) { 'bokser' => '🥊 Bokser — Styl: Presja', 'obronca' => '🛡️ Obrońca — Styl: Kontrola', 'szybki' => '⚡ Szybki — Styl: Kontra', _ => c };

class _TileData {
  _TileData(this.cat, this.id, this.icon, this.title, this.subtitle, this.locked, this.sheet, {this.page = false});
  final String cat, id, icon, title, subtitle; // cat: train | duel | mini
  final bool locked;
  final bool page; // true = podstrona /club/<id> wewnątrz ShellRoute (menu zostaje)
  final Widget Function() sheet;
}

/// Kafelek dyscypliny — ten sam styl i wysokość dla wszystkich.
class _Tile extends StatefulWidget {
  const _Tile({super.key, required this.t, required this.onTap});
  final _TileData t;
  final VoidCallback onTap;
  @override
  State<_Tile> createState() => _TileState();
}

class _TileState extends State<_Tile> {
  bool _hover = false;
  @override
  Widget build(BuildContext context) {
    final t = widget.t;
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: _hover ? AppColors.surfaceLight : AppColors.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: _hover ? AppColors.primary : AppColors.border),
          ),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(t.icon, style: const TextStyle(fontSize: 40)),
            const SizedBox(height: 8),
            Text(t.title, textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 4),
            Text(t.locked ? '🔒 ${t.subtitle}' : t.subtitle, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11, color: t.locked ? AppColors.warning : AppColors.textSecondary)),
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Wspólne
// ---------------------------------------------------------------------------
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
          const SizedBox(height: 8),
          ...children,
        ]),
      );
}

void showClubResult(BuildContext context, ClubResult r) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(r.message),
      backgroundColor: r.ok ? AppColors.surfaceLight : AppColors.danger.withValues(alpha: 0.9),
      behavior: SnackBarBehavior.floating,
    ));
}

/// Wykonuje akcję; walka → zamyka modal i otwiera FightScreen, błąd → SnackBar.
Future<void> runClub(BuildContext context, Future<ClubResult> f, {bool closeOnFight = true}) async {
  final nav = Navigator.of(context);
  final messenger = ScaffoldMessenger.of(context);
  final r = await f;
  if (r.fight != null) {
    if (closeOnFight && nav.canPop()) nav.pop();
    if (nav.mounted) await openFight(nav.context, r.fight!);
    return;
  }
  messenger
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(r.message),
      backgroundColor: r.ok ? AppColors.surfaceLight : AppColors.danger.withValues(alpha: 0.9),
      behavior: SnackBarBehavior.floating,
    ));
}


// ---------------------------------------------------------------------------
// PvP: wybór klasy (jednorazowo) + lista przeciwników + Atakuj
// ---------------------------------------------------------------------------
class PvpSheet extends ConsumerStatefulWidget {
  const PvpSheet({super.key});
  @override
  ConsumerState<PvpSheet> createState() => _PvpSheetState();
}

class _PvpSheetState extends ConsumerState<PvpSheet> {
  int? _busy;
  String? _pick;

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(clubProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    if (d.level < 2) {
      return const _Frame(title: '⚔️ Pojedynki PvP', children: [
        Text('🔒 PvP odblokowuje się na 2. poziomie. Zdobywaj XP w kontraktach, treningach i Lochu.', style: TextStyle(color: AppColors.warning)),
      ]);
    }
    if (d.classType == null) return _classPicker();
    final left = ClubData.dailyLimit - d.dailyUsed;
    return _Frame(title: '⚔️ Pojedynki PvP', children: [
      Text('Klasa = Taktyka: ${_classLabel(d.classType!)} · walk dziś: ${d.dailyUsed}/${ClubData.dailyLimit} · z jednym rywalem max 4 / 24 h',
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      const SizedBox(height: 10),
      if (d.targets.isEmpty) const Text('Brak przeciwników w tym świecie.', style: TextStyle(color: AppColors.textSecondary)),
      for (final t in d.targets)
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
          child: Row(children: [
            CircleAvatar(
              backgroundColor: AppColors.surface,
              child: Text(switch ('${t['cls']}') { 'Obrońca' => '🛡️', 'Szybki' => '⚡', _ => '🥊' }),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${t['nickname']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('Lvl ${t['level']} · ${t['cls']} · Elo ~${t['rating']}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              ]),
            ),
            FilledButton(
              key: Key('attack-${t['id']}'),
              style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
              onPressed: _busy != null || left <= 0
                  ? null
                  : () async {
                      setState(() => _busy = t['id'] as int);
                      await runClub(context, ref.read(clubActionsProvider).attack(t['id'] as int, '${t['nickname']}'));
                      if (mounted) setState(() => _busy = null);
                    },
              child: Text(_busy == t['id'] ? '…' : 'Atakuj'),
            ),
          ]),
        ),
    ]);
  }

  Widget _classPicker() {
    const classes = [
      ('bokser', '🥊', 'Bokser', 'Styl: Presja · Siła 14', '1/6 szansy na Mocny Cios (×1,6) i +12% obrażeń'),
      ('obronca', '🛡️', 'Obrońca', 'Styl: Kontrola · Inteligencja 14', '−20% otrzymywanych obrażeń, 1/8 szansy na Kontrę po bloku'),
      ('szybki', '⚡', 'Szybki', 'Styl: Kontra · Refleks 14', '30% szansy na Kontrę po uniku, unik +8 pp, crit rośnie z każdym trafieniem'),
    ];
    return _Frame(title: '⚔️ PvP odblokowane — wybierz klasę', children: [
      const Text('Klasa to Twoja taktyka w każdej walce. Wybór jest jednorazowy i nieodwracalny.',
          style: TextStyle(color: AppColors.textSecondary)),
      const SizedBox(height: 10),
      for (final c in classes)
        GestureDetector(
          key: Key('class-${c.$1}'),
          onTap: () => setState(() => _pick = c.$1),
          child: Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: _pick == c.$1 ? AppColors.primary.withValues(alpha: .12) : AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: _pick == c.$1 ? AppColors.primary : AppColors.border, width: _pick == c.$1 ? 2 : 1),
            ),
            child: Row(children: [
              Text(c.$2, style: const TextStyle(fontSize: 30)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${c.$3} · ${c.$4}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(c.$5, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                ]),
              ),
            ]),
          ),
        ),
      const SizedBox(height: 6),
      FilledButton(
        key: const Key('class-confirm'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
        onPressed: _pick == null || _busy != null
            ? null
            : () async {
                final ok = await showDialog<bool>(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: const Text('Potwierdź klasę'),
                    content: Text('Wybierasz: ${_classLabel(_pick!)}. Tej decyzji nie można cofnąć.'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Anuluj')),
                      FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Wybieram')),
                    ],
                  ),
                );
                if (ok != true || !mounted) return;
                setState(() => _busy = 0);
                final r = await ref.read(clubActionsProvider).pickClass(_pick!);
                if (!mounted) return;
                setState(() => _busy = null);
                showClubResult(context, r);
              },
        child: const Text('Wybieram tę klasę'),
      ),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Loch: Normal / Hard / Nightmare + następne piętro + rekord
// ---------------------------------------------------------------------------
class DungeonSheet extends ConsumerStatefulWidget {
  const DungeonSheet({super.key});
  @override
  ConsumerState<DungeonSheet> createState() => _DungeonSheetState();
}

class _DungeonSheetState extends ConsumerState<DungeonSheet> {
  String _mode = 'normal';
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(clubProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    const modes = [('normal', 'Normal', '🟢'), ('hard', 'Hard', '🟠'), ('nightmare', 'Nightmare', '🔴')];
    final m = d.mode(_mode);
    final nxt = (m['nextFloor'] as Map?) ?? const {};
    final locked = m['locked'] == true;
    final energy = (m['energy'] as num?)?.toInt() ?? 0;
    return _Frame(title: '🐉 Ring / Loch', children: [
      SegmentedButton<String>(
        showSelectedIcon: false,
        segments: [
          for (final x in modes)
            ButtonSegment(
              value: x.$1,
              label: Text('${x.$3} ${x.$2}${d.mode(x.$1)['locked'] == true ? ' 🔒' : ''}', style: const TextStyle(fontSize: 12)),
            ),
        ],
        selected: {_mode},
        onSelectionChanged: (v) => setState(() => _mode = v.first),
      ),
      const SizedBox(height: 12),
      Text('Koszt: $energy⚡ · wymagany poziom ${m['reqLevel']} · Twój poziom ${d.level}',
          style: TextStyle(color: locked ? AppColors.warning : AppColors.textSecondary)),
      const SizedBox(height: 6),
      MeterBar(
        value: ((m['best'] as num?) ?? 0) / (((m['floors'] as num?) ?? 1).clamp(1, 1000)),
        color: AppColors.gold,
        height: 8,
        label: '🏅 Rekord: piętro ${m['best']} / ${m['floors']}',
      ),
      const SizedBox(height: 12),
      if (m['completed'] == true)
        const Text('Tryb opanowany w 100%!', style: TextStyle(color: AppColors.gold, fontWeight: FontWeight.w800))
      else if (nxt.isNotEmpty)
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12), border: Border.all(color: nxt['boss'] == true ? AppColors.danger : AppColors.border)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Następne piętro ${nxt['n']}${nxt['boss'] == true ? ' · 👑 BOSS' : ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
            Text('${nxt['name']} · ${nxt['cls']} · seria ${nxt['series']} (${nxt['theme']})', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            const SizedBox(height: 4),
            Text('Nagroda: ${money((nxt['cash'] as num?) ?? 0)} · ${nxt['xp']} XP${_mode == 'normal' ? ' · szansa na drop z setów' : ''}',
                style: const TextStyle(fontSize: 12, color: AppColors.success)),
          ]),
        ),
      const SizedBox(height: 14),
      FilledButton(
        key: const Key('dungeon-start'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50), backgroundColor: AppColors.danger),
        onPressed: _busy || locked || m['completed'] == true || d.energy < energy
            ? null
            : () async {
                setState(() => _busy = true);
                await runClub(context, ref.read(clubActionsProvider).dungeon(_mode));
                if (mounted) setState(() => _busy = false);
              },
        child: Text(_busy ? 'Schodzę…' : (d.energy < energy ? 'Za mało energii' : '⚔️ WALCZ O PIĘTRO')),
      ),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Boks / MMA: turniej (seria walk w FightScreen)
// ---------------------------------------------------------------------------
class BoxingSheet extends ConsumerStatefulWidget {
  const BoxingSheet({super.key});
  @override
  ConsumerState<BoxingSheet> createState() => _BoxingSheetState();
}

class _BoxingSheetState extends ConsumerState<BoxingSheet> {
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    final d = ref.watch(clubProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final t = (d.sports['tourn'] as Map?) ?? const {};
    final runs = (t['runs'] as num?)?.toInt() ?? 0;
    return _Frame(title: '🥊 Boks / MMA', children: [
      const Text('Turniej: seria walk z zawodnikami klubu. Wpisowe 200 \$, 30⚡. Limit 2 turnieje na dobę.',
          style: TextStyle(color: AppColors.textSecondary)),
      const SizedBox(height: 8),
      Text('Dziś: $runs/2 · najlepszy wynik: ${t['best'] ?? 0} wygranych', style: const TextStyle(fontWeight: FontWeight.w700)),
      if (d.level < 2) const Padding(padding: EdgeInsets.only(top: 6), child: Text('🔒 Od 2. poziomu.', style: TextStyle(color: AppColors.warning))),
      const SizedBox(height: 14),
      FilledButton(
        key: const Key('boxing-start'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(50)),
        onPressed: _busy || runs >= 2 || d.level < 2
            ? null
            : () async {
                setState(() => _busy = true);
                await runClub(context, ref.read(clubActionsProvider).tournament(d.nickname));
                if (mounted) setState(() => _busy = false);
              },
        child: Text(_busy ? 'Wchodzę na ring…' : '🔔 WEJDŹ DO TURNIEJU'),
      ),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Siłownia: trening 5 statystyk (kolejka 4) + odbiór ukończonych
// ---------------------------------------------------------------------------
class GymSheet extends ConsumerStatefulWidget {
  const GymSheet({super.key});
  @override
  ConsumerState<GymSheet> createState() => _GymSheetState();
}

class _GymSheetState extends ConsumerState<GymSheet> {
  bool _busy = false;
  Future<void> _go(Future<ClubResult> f) async {
    setState(() => _busy = true);
    final r = await f;
    if (!mounted) return;
    ref.invalidate(gearProvider); // nowa baza → nowe rozbicie statystyk
    setState(() => _busy = false);
    showClubResult(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(clubProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final q = d.training;
    final now = DateTime.now().millisecondsSinceEpoch;
    // łączne statystyki z rozbiciem (te same dane co w Ekwipunku)
    final parts = ref.watch(gearProvider).valueOrNull?.statBreakdown ?? const <StatPart>[];
    return _Frame(title: '🏋️ Siłownia', children: [
      const Text('Trening natychmiastowy: 5⚡ + opłata · od razu +1 do statystyki. Im wyższa statystyka, tym drożej (50 \$ + 15 \$ za każdy punkt).',
          style: TextStyle(color: AppColors.textSecondary)),
      const SizedBox(height: 12),
      for (var i = 0; i < 5; i++)
        Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
          child: Row(children: [
            Text(statIcons[i], style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (i < parts.length)
                  StatValue(
                    key: Key('gym-stat-$i'),
                    p: parts[i],
                    child: Text.rich(TextSpan(children: [
                      TextSpan(text: '${statNames[i]}: ${parts[i].totalText}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      if (parts[i].boosted)
                        TextSpan(text: '  (trening ${i < d.stats.length ? d.stats[i].round() : '-'} ⓘ)', style: const TextStyle(fontSize: 11, color: AppColors.success)),
                    ])),
                  )
                else
                  Text('${statNames[i]}: ${i < d.stats.length ? d.stats[i].round() : '-'}', style: const TextStyle(fontWeight: FontWeight.w800)),
                Text(statHelp[i], key: Key('stat-help-$i'), style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              ]),
            ),
            const SizedBox(width: 8),
            FilledButton(
              key: Key('train-$i'),
              onPressed: _busy || d.energy < 5 || (i < d.gymCosts.length && d.cash < d.gymCosts[i]) ? null : () => _go(ref.read(clubActionsProvider).train(i)),
              child: Text(i < d.gymCosts.length ? '+1 · ${d.gymCosts[i]} \$' : 'Trenuj'),
            ),
          ]),
        ),
      // zgodność wsteczna: treningi zakolejkowane przed zmianą można nadal odebrać
      if (q.isNotEmpty) ...[
        const SizedBox(height: 6),
        const Text('STARE TRENINGI W KOLEJCE', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
        for (final t in q)
          Row(children: [
            Expanded(child: Text('${statIcons[(t['stat'] as num).toInt()]} ${statNames[(t['stat'] as num).toInt()]}')),
            if (((t['end'] as num?) ?? 0) <= now)
              TextButton(onPressed: _busy ? null : () => _go(ref.read(clubActionsProvider).claimTraining((t['id'] as num).toInt())), child: const Text('Odbierz +1'))
            else
              Text('${(((t['end'] as num) - now) / 1000).ceil()} s', style: const TextStyle(color: AppColors.textSecondary)),
          ]),
      ],
    ]);
  }
}

/// QA 3: krótkie wyjaśnienie statystyk (GDD).
const statHelp = [
  'Obrażenia, Mocny Cios, szybsze kontrakty',
  'Redukcja obrażeń, efektywność firm i budowy',
  'Inicjatywa, unik, szybszy transport',
  'Punkty życia (HP), lepsze zarobki NPC',
  'Trafienie krytyczne, lepsze kontrakty',
];

// ---------------------------------------------------------------------------
// QA 5: Łucznictwo / Pływanie — 3 podejścia na dobę (od razu · po 5 min · po 15 min), reset o północy
// ---------------------------------------------------------------------------
class SportSheet extends ConsumerStatefulWidget {
  const SportSheet({super.key, required this.kind});
  final String kind; // archery | swim
  @override
  ConsumerState<SportSheet> createState() => _SportSheetState();
}

class _SportSheetState extends ConsumerState<SportSheet> {
  bool _busy = false;
  String? _last;
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(seconds: 1), (_) { if (mounted) setState(() {}); });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  Future<void> _go(bool skip) async {
    setState(() => _busy = true);
    final a = ref.read(clubActionsProvider);
    final r = await (widget.kind == 'archery' ? a.archery(skip: skip) : a.swim(skip: skip));
    if (!mounted) return;
    setState(() { _busy = false; _last = r.message; });
    if (!r.ok) showClubResult(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(clubProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final archery = widget.kind == 'archery';
    final m = ((d.sports[archery ? 'archery' : 'swim3'] as Map?) ?? const {}).cast<String, dynamic>();
    final n = _i(m['n']);
    final readyAt = m['readyAt'] == null ? null : _i(m['readyAt']);
    final now = DateTime.now().millisecondsSinceEpoch;
    final wait = readyAt == null ? 0 : ((readyAt - now) / 1000).ceil();
    final coupons = _i(m['coupons']);
    final steps = archery ? const ['+3% maks. energii', '+6% maks. energii', '+10% maks. energii'] : const ['+3% stat. · +1% regen.', '+6% stat. · +3% regen.', '+10% stat. · +5% regen.'];
    String fmt(int sec) => sec >= 60 ? '${sec ~/ 60} min ${sec % 60} s' : '$sec s';
    return _Frame(title: archery ? '🎯 Łucznictwo' : '🏊 Pływanie', children: [
      Text(
        archery
            ? 'Każda seria: natychmiast +20% energii i rosnący limit maks. energii (stack do północy). Bez opłat.'
            : 'Każda seria: buff do statystyki klasowej i szybsza regeneracja energii (stack do północy). Bez opłat.',
        style: const TextStyle(color: AppColors.textSecondary),
      ),
      const SizedBox(height: 12),
      for (var k = 0; k < 3; k++)
        Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: k < n ? AppColors.success.withValues(alpha: .12) : AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: k < n ? AppColors.success : (k == n ? AppColors.primary : AppColors.border)),
          ),
          child: Row(children: [
            Text(k < n ? '✅' : (k == n ? '▶️' : '⏳'), style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 10),
            Expanded(child: Text('Seria ${k + 1}: ${steps[k]}', style: const TextStyle(fontWeight: FontWeight.w700))),
            Text(k == 0 ? 'od razu' : (k == 1 ? 'po 5 min' : 'po 15 min'), style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          ]),
        ),
      if (archery && m['energyMax'] != null)
        Text('Maks. energia dziś: ${m['energyMax']} (+${m['maxPct'] ?? 0}%)', style: const TextStyle(fontWeight: FontWeight.w700)),
      if (!archery && _i(m['statPct']) > 0)
        Text('Aktywny buff: ${statNames[_i(m['stat'])]} +${m['statPct']}% · regeneracja +${m['regenPct']}%', style: const TextStyle(fontWeight: FontWeight.w700)),
      if (_last != null) ...[
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(10)),
          child: Text(_last!, style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
      ],
      const SizedBox(height: 14),
      if (n >= 3)
        const Text('Wszystkie 3 serie wykorzystane — nowe po północy.', textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary))
      else if (wait > 0) ...[
        FilledButton(onPressed: null, style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)), child: Text('Następna seria za ${fmt(wait)}')),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          key: Key('sport-skip-${widget.kind}'),
          onPressed: _busy || coupons < 1 ? null : () => _go(true),
          icon: const Text('🎟️'),
          label: Text(coupons < 1 ? 'Brak Kuponu Akcji (kup w Sklepie)' : 'Pomiń czekanie — Kupon Akcji ($coupons)'),
        ),
      ] else
        FilledButton(
          key: Key('sport-${widget.kind}'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          onPressed: _busy ? null : () => _go(false),
          child: Text(_busy ? '…' : 'Rozpocznij serię ${n + 1}/3'),
        ),
    ]);
  }
}

int _i(Object? v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;

String _left(Map m) {
  final ms = _i(m['resetAt']) - DateTime.now().millisecondsSinceEpoch;
  final min = (ms / 60000).ceil().clamp(0, 999);
  return min >= 60 ? '${min ~/ 60} h ${min % 60} min' : '$min min';
}

// ---------------------------------------------------------------------------
// QA 5: Agility psów — psiarnia, rasy, szkolenie, smaczek, limit 10 / 4 h
// ---------------------------------------------------------------------------
class DogSheet extends ConsumerStatefulWidget {
  const DogSheet({super.key});
  @override
  ConsumerState<DogSheet> createState() => _DogSheetState();
}

class _DogSheetState extends ConsumerState<DogSheet> {
  bool _busy = false;
  bool _treat = false;
  String? _last;

  Future<void> _go(Future<ClubResult> f, {bool keep = false}) async {
    setState(() => _busy = true);
    final r = await f;
    if (!mounted) return;
    setState(() { _busy = false; if (keep || r.ok) _last = r.message; });
    if (!r.ok) showClubResult(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(sports3Provider);
    final a = ref.read(clubActionsProvider);
    final d = ref.watch(clubProvider).valueOrNull;
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
      error: (e, _) => _Frame(title: '🐕 Agility psów', children: [ErrorBanner('$e')]),
      data: (s) {
        final rules = (s['rules'] as Map?) ?? const {};
        final ag = (s['agility'] as Map?) ?? const {};
        final dogs = [for (final x in (s['dogs'] as List?) ?? const []) (x as Map).cast<String, dynamic>()];
        final dog = dogs.where((x) => x['active'] == true).firstOrNull ?? (dogs.isEmpty ? null : dogs.first);
        final breeds = [for (final x in (s['breeds'] as List?) ?? const []) (x as Map).cast<String, dynamic>()];
        final owned = {for (final x in dogs) x['breed']};
        final entry = _i(rules['agilityEntry']) + (_treat ? _i(rules['treatCost']) : 0);
        final left = _i(ag['left']);
        final canRun = !_busy && left > 0 && (d?.energy ?? 0) >= _i(rules['agilityEnergy']) && (d?.cash ?? 0) >= entry;
        const labels = {'speed': '💨 Szybkość', 'stamina': '🫀 Wytrzymałość', 'obedience': '🎓 Posłuszeństwo'};
        return _Frame(title: '🐕 Agility psów', children: [
          Text('Tor przeszkód: wpisowe ${rules['agilityEntry']} \$ · ${rules['agilityEnergy']}⚡. Wynik zależy od statystyk psa (i trochę od Twojego Refleksu).',
              style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 8),
          Text('Konkursy: ${ag['runs']}/${ag['limit']} w tym oknie · reset za ${_left(ag)} · rekord ${ag['best']} pkt',
              key: const Key('agility-window'), style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          if (dog != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.primary)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('Aktywny: ${dog['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                const SizedBox(height: 6),
                for (final k in const ['speed', 'stamina', 'obedience'])
                  Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(children: [
                      SizedBox(width: 130, child: Text(labels[k]!)),
                      Expanded(child: MeterBar(value: _i(dog[k]) / _i(rules['dogStatCap'] ?? 20), color: AppColors.primary, label: '${dog[k]}/${rules['dogStatCap']}')),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        key: Key('dog-train-$k'),
                        onPressed: _busy || _i(dog[k]) >= _i(rules['dogStatCap']) ? null : () => _go(a.dogTrain(k)),
                        child: Text('Szkolenie ${((dog['trainCost'] as Map?) ?? const {})[k]} \$'),
                      ),
                    ]),
                  ),
              ]),
            ),
          const SizedBox(height: 10),
          CheckboxListTile(
            key: const Key('dog-treat'),
            contentPadding: EdgeInsets.zero,
            value: _treat,
            onChanged: (v) => setState(() => _treat = v ?? false),
            title: Text('🦴 Smaczek dla psa (+${rules['treatCost']} \$) — wynik +${rules['treatPct']}%'),
          ),
          if (_last != null)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(10)),
              child: Text(_last!, style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          FilledButton(
            key: const Key('sport-agility'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            onPressed: canRun ? () => _go(a.agility(treat: _treat), keep: true) : null,
            child: Text(left <= 0 ? 'Limit wykorzystany — reset za ${_left(ag)}' : 'Start na torze ($entry \$ · ${rules['agilityEnergy']}⚡)'),
          ),
          const SizedBox(height: 16),
          const Text('PSIARNIA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          for (final x in dogs)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${x['name']}${x['premium'] == true ? ' ✨' : ''}'),
              subtitle: Text('💨 ${x['speed']} · 🫀 ${x['stamina']} · 🎓 ${x['obedience']}'),
              trailing: x['active'] == true
                  ? const Text('aktywny', style: TextStyle(color: AppColors.success))
                  : TextButton(onPressed: _busy ? null : () => _go(a.dogPick('${x['key']}')), child: const Text('Wybierz')),
            ),
          const SizedBox(height: 8),
          const Text('NOWE RASY', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          for (final b in breeds)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: Text('${b['icon']}', style: const TextStyle(fontSize: 24)),
              title: Text('${b['name']} · od lvl ${b['level']}'),
              subtitle: Text('💨 ${b['speed']} · 🫀 ${b['stamina']} · 🎓 ${b['obedience']} — ${b['desc']}'),
              trailing: owned.contains(b['id'])
                  ? const Text('w psiarni', style: TextStyle(color: AppColors.textSecondary))
                  : FilledButton(
                      key: Key('dog-buy-${b['id']}'),
                      onPressed: _busy || d == null || d.level < _i(b['level']) || d.cash < _i(b['price']) ? null : () => _go(a.dogBuy('${b['id']}')),
                      child: Text('${b['price']} \$'),
                    ),
            ),
        ]);
      },
    );
  }
}

// ---------------------------------------------------------------------------
// QA 5: Jazda Konna — szybki konkurs na statystykach konia (bez zakładów)
// ---------------------------------------------------------------------------
const _horseShop = [
  ('mustang', 'Mustang', 800, 5, 3, 3),
  ('thoroughbred', 'Pełnej krwi', 3000, 6, 5, 4),
  ('champion', 'Czempion', 8000, 8, 6, 6),
];

class RidingSheet extends ConsumerStatefulWidget {
  const RidingSheet({super.key});
  @override
  ConsumerState<RidingSheet> createState() => _RidingSheetState();
}

class _RidingSheetState extends ConsumerState<RidingSheet> {
  bool _busy = false;
  String? _last;

  Future<void> _go(Future<ClubResult> f, {bool keep = false}) async {
    setState(() => _busy = true);
    final r = await f;
    if (!mounted) return;
    setState(() { _busy = false; if (keep || r.ok) _last = r.message; });
    if (!r.ok) showClubResult(context, r);
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(sports3Provider);
    final a = ref.read(clubActionsProvider);
    final d = ref.watch(clubProvider).valueOrNull;
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
      error: (e, _) => _Frame(title: '🏇 Jazda Konna', children: [ErrorBanner('$e')]),
      data: (s) {
        final rules = (s['rules'] as Map?) ?? const {};
        final rd = (s['riding'] as Map?) ?? const {};
        final horse = (s['horse'] as Map?) ?? const {};
        final stable = [for (final x in (s['stable'] as List?) ?? const []) (x as Map).cast<String, dynamic>()];
        final left = _i(rd['left']);
        final can = !_busy && left > 0 && (d?.energy ?? 0) >= _i(rules['ridingEnergy']) && (d?.cash ?? 0) >= _i(rules['ridingEntry']);
        return _Frame(title: '🏇 Jazda Konna', children: [
          Text('Konkurs na torze z przeszkodami: wpisowe ${rules['ridingEntry']} \$ · ${rules['ridingEnergy']}⚡. Wynik = szybkość i wytrzymałość konia + Twój Refleks i Charyzma. Nagroda: \$ + XP.',
              style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 8),
          Text('Przejazdy: ${rd['runs']}/${rd['limit']} w tym oknie · reset za ${_left(rd)} · rekord ${rd['best']} pkt',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.primary)),
            child: Row(children: [
              const Text('🐎', style: TextStyle(fontSize: 32)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${horse['name']}', style: const TextStyle(fontWeight: FontWeight.w900)),
                  Text('💨 Szybkość ${horse['speed']} · 🫀 Wytrzymałość ${horse['stamina']}'),
                  if (horse['starter'] == true) const Text('Kup własnego konia, by mieć lepsze wyniki.', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                ]),
              ),
            ]),
          ),
          if (_last != null)
            Container(
              margin: const EdgeInsets.only(top: 10),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(10)),
              child: Text(_last!, style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          const SizedBox(height: 12),
          FilledButton(
            key: const Key('sport-riding'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            onPressed: can ? () => _go(a.riding(), keep: true) : null,
            child: Text(left <= 0 ? 'Limit wykorzystany — reset za ${_left(rd)}' : 'Start (${rules['ridingEntry']} \$ · ${rules['ridingEnergy']}⚡)'),
          ),
          if (stable.length > 1) ...[
            const SizedBox(height: 16),
            const Text('STAJNIA', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
            for (final x in stable)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('${x['name']}'),
                subtitle: Text('💨 ${x['speed']} · 🫀 ${x['stamina']}'),
                trailing: x['name'] == horse['name']
                    ? const Text('aktywny', style: TextStyle(color: AppColors.success))
                    : TextButton(onPressed: _busy ? null : () => _go(a.pickHorse('${x['key']}')), child: const Text('Wybierz')),
              ),
          ],
          const SizedBox(height: 12),
          const Text('KONIE NA SPRZEDAŻ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          for (final (id, name, price, lvl, sp, st) in _horseShop)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('$name · od lvl $lvl'),
              subtitle: Text('💨 $sp · 🫀 $st'),
              trailing: stable.any((x) => x['breed'] == id)
                  ? const Text('w stajni', style: TextStyle(color: AppColors.textSecondary))
                  : FilledButton(
                      key: Key('horse-buy-$id'),
                      onPressed: _busy || d == null || d.level < lvl || d.cash < price ? null : () => _go(a.buyHorse(id)),
                      child: Text('$price \$'),
                    ),
            ),
        ]);
      },
    );
  }
}
