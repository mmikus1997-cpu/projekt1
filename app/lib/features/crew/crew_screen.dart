import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart';
import 'crew_models.dart';
import 'crew_providers.dart';
import 'crew_sheets.dart';
import 'npc_card.dart';

/// Ekran „Ekipa” (GDD v3.2): siatka NPC, akcje zbiorcze, porady asystenta, rekrutacja.
/// Kolumny: 1 (mobile < 600), 2 (tablet), 3 (desktop ≥ 1100).
class CrewScreen extends ConsumerStatefulWidget {
  const CrewScreen({super.key});
  @override
  ConsumerState<CrewScreen> createState() => _CrewScreenState();
}

class _CrewScreenState extends ConsumerState<CrewScreen> {
  Timer? _tick, _poll;
  int now = DateTime.now().millisecondsSinceEpoch;

  @override
  void initState() {
    super.initState();
    // zegar co 30 s (pozostały czas zmian) + odświeżanie stanu ekipy co 60 s
    _tick = Timer.periodic(const Duration(seconds: 30), (_) => setState(() => now = DateTime.now().millisecondsSinceEpoch));
    _poll = Timer.periodic(const Duration(seconds: 60), (_) => ref.invalidate(crewProvider));
  }

  @override
  void dispose() {
    _tick?.cancel();
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _act(Future<CrewResult> f) async {
    final r = await f;
    if (mounted) showCrewResult(context, r);
  }

  void _openNpc(Npc n, CrewData d) {
    if (n.busy) {
      _showBusy(n, d);
    } else if (n.isDriver) {
      showCrewModal(context, TaxiSheet(npc: n, data: d));
    } else {
      showCrewModal(context, DispatchSheet(npc: n, data: d));
    }
  }

  void _showBusy(Npc n, CrewData d) {
    final (status, icon, color) = npcStatus(n, d, now);
    showCrewModal(
      context,
      Padding(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            NpcAvatar(n, size: 44),
            const SizedBox(width: 12),
            Expanded(child: Text(n.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
          const SizedBox(height: 14),
          Row(children: [Icon(icon, color: color), const SizedBox(width: 8), Expanded(child: Text(status, style: TextStyle(color: color)))]),
          const SizedBox(height: 18),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger, minimumSize: const Size.fromHeight(46)),
            icon: const Icon(Icons.stop_circle_outlined),
            label: Text(n.duty == 'taxi' ? 'ZAKOŃCZ TAXI (wypłata za przejechane godziny)' : 'ODWOŁAJ DO REZYDENCJI'),
            onPressed: () {
              Navigator.pop(context);
              _act(ref.read(crewActionsProvider).recall(n.id));
            },
          ),
        ]),
      ),
    );
  }

  void _menu(Npc n, String action) {
    final a = ref.read(crewActionsProvider);
    switch (action) {
      case 'recall':
        _act(a.recall(n.id));
      case 'feed':
        _act(a.feed(n.id));
      case 'role':
        _act(a.setRole(n.id, n.isDriver ? 'service' : 'driver'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(crewProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(crewProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
      ),
      data: (d) => RefreshIndicator(
        onRefresh: () => ref.refresh(crewProvider.future),
        child: LayoutBuilder(builder: (context, c) {
          final cols = c.maxWidth >= 1100 ? 3 : (c.maxWidth >= 600 ? 2 : 1);
          final pad = cols == 1 ? 14.0 : 24.0;
          final cardW = (c.maxWidth - pad * 2 - 14 * (cols - 1)) / cols;
          final npcs = [...d.npcs]..sort((a, b) => (a.busy ? 1 : 0).compareTo(b.busy ? 1 : 0));
          return ListView(
            padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 70),
            children: [
              _Header(d: d, onRecruit: () => showCrewModal(context, RecruitSheet(data: d))),
              const SizedBox(height: 14),
              _BatchBar(
                data: d,
                onCollect: () => _act(ref.read(crewActionsProvider).collect()),
                onFeed: () => _act(ref.read(crewActionsProvider).batch({'action': 'all_to_buffet', 'npcs': 'all'})),
                onSleep: () => _confirmSleep(d),
                onTransport: () => showCrewModal(context, TransportAllSheet(data: d)),
              ),
              const SizedBox(height: 14),
              _AssistantCard(data: d, onApply: (tip) => _applyTip(tip, d)),
              const SizedBox(height: 18),
              if (npcs.isEmpty)
                _EmptyCrew(onRecruit: () => showCrewModal(context, RecruitSheet(data: d)))
              else
                Wrap(spacing: 14, runSpacing: 14, children: [
                  for (final n in npcs)
                    SizedBox(
                      width: cardW,
                      child: NpcCard(n: n, data: d, now: now, onTap: () => _openNpc(n, d), onMenu: (a) => _menu(n, a)),
                    ),
                ]),
              if (npcs.isNotEmpty) ...[
                const SizedBox(height: 16),
                Center(
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(minimumSize: const Size(260, 50)),
                    onPressed: () => showCrewModal(context, RecruitSheet(data: d)),
                    icon: const Icon(Icons.person_add_alt_1_rounded),
                    label: Text(d.nextCost == null
                        ? '+ Zrekrutuj Pracownika (${d.count}/${d.slots} — brak miejsc)'
                        : '+ Zrekrutuj Pracownika · ${money(d.nextCost!)} · ${d.count}/${d.slots}'),
                  ),
                ),
              ],
              if (d.rides.isNotEmpty) ...[
                const SizedBox(height: 18),
                _RidesCard(data: d, now: now),
              ],
            ],
          );
        }),
      ),
    );
  }

  Future<void> _confirmSleep(CrewData d) async {
    final busy = d.npcs.where((n) => n.busy).length;
    if (busy == 0) {
      showCrewResult(context, const CrewResult('Cała ekipa już odpoczywa w Rezydencji.'));
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Wszyscy do snu?'),
        content: Text('Odwołasz $busy NPC do Rezydencji. Zmiany kończą się wcześniej — wypłata za przepracowany czas, bez bonusu auto-pilota.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Anuluj')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Odwołaj')),
        ],
      ),
    );
    if (ok == true) _act(ref.read(crewActionsProvider).batch({'action': 'recall', 'npcs': 'all'}));
  }

  void _applyTip(AssistantTip tip, CrewData d) {
    final n = d.npcs.where((x) => x.id == tip.npcId).firstOrNull;
    if (n == null) return;
    _act(ref.read(crewActionsProvider).dispatch(n.id, tip.serviceId, tip.hours, car: tip.car));
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.d, required this.onRecruit});
  final CrewData d;
  final VoidCallback onRecruit;
  @override
  Widget build(BuildContext context) {
    final working = d.npcs.where((n) => n.onShift).length;
    final taxi = d.npcs.where((n) => n.duty == 'taxi').length;
    final loyal = d.npcs.where((n) => n.loyal).length;
    Widget stat(String icon, String label, String value, [Color? c]) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text(icon, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 6),
            Text(value, style: TextStyle(fontWeight: FontWeight.w900, color: c ?? AppColors.textPrimary)),
            const SizedBox(width: 4),
            Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ]),
        );
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      crossAxisAlignment: WrapCrossAlignment.center,
      alignment: WrapAlignment.spaceBetween,
      children: [
        Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
          const Text('Ekipa', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
          const SizedBox(width: 4),
          stat('👥', 'w Rezydencji', '${d.count}/${d.slots}'),
          stat('🛠️', 'w pracy', '$working', AppColors.success),
          stat('🚗', 'kierowców wolnych', '${d.driversFree}/${d.driversTotal}', AppColors.gold),
          if (taxi > 0) stat('🚕', 'na Taxi', '$taxi', AppColors.gold),
          if (loyal > 0) stat('👑', 'lojalnych', '$loyal', AppColors.gold),
        ]),
        FilledButton.icon(
          onPressed: onRecruit,
          icon: const Icon(Icons.person_add_alt_1_rounded),
          label: Text(d.nextCost == null ? 'Zrekrutuj (brak miejsc)' : 'Zrekrutuj Pracownika · ${money(d.nextCost!)}'),
        ),
      ],
    );
  }
}

class _BatchBar extends StatelessWidget {
  const _BatchBar({required this.data, required this.onCollect, required this.onFeed, required this.onSleep, required this.onTransport});
  final CrewData data;
  final VoidCallback onCollect, onFeed, onSleep, onTransport;
  @override
  Widget build(BuildContext context) {
    Widget btn(String icon, String label, VoidCallback? f, {Color? c}) => OutlinedButton(
          style: OutlinedButton.styleFrom(
            foregroundColor: c ?? AppColors.textPrimary,
            side: BorderSide(color: (c ?? AppColors.primary).withValues(alpha: 0.6)),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          onPressed: f,
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text(icon, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 8),
            Flexible(child: Text(label, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
        );
    final empty = data.npcs.isEmpty;
    return SectionCard(
      title: 'Akcje zbiorcze',
      icon: Icons.groups_rounded,
      child: LayoutBuilder(builder: (context, c) {
        final buttons = [
          btn('💰', 'Odbierz wszystkich', empty ? null : onCollect, c: AppColors.success),
          btn('🍱', 'Wszyscy do jedzenia', empty ? null : onFeed),
          btn('😴', 'Wszyscy do snu', empty ? null : onSleep),
          btn('🚐', 'Zawieź do miasta', empty ? null : onTransport, c: AppColors.gold),
        ];
        if (c.maxWidth >= 560) return Wrap(spacing: 10, runSpacing: 10, children: buttons);
        // mobile: 2×2, przyciski równej szerokości
        Widget row(Widget a, Widget b) => Row(children: [Expanded(child: a), const SizedBox(width: 8), Expanded(child: b)]);
        return Column(children: [row(buttons[0], buttons[1]), const SizedBox(height: 8), row(buttons[2], buttons[3])]);
      }),
    );
  }
}

class _AssistantCard extends ConsumerWidget {
  const _AssistantCard({required this.data, required this.onApply});
  final CrewData data;
  final void Function(AssistantTip) onApply;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tips = data.tips;
    final alerts = data.alerts.take(3).toList();
    final hours = ref.watch(crewTipHoursProvider);
    return SectionCard(
      title: '💡 Porady Asystenta',
      trailing: SegmentedButton<int>(
        showSelectedIcon: false,
        style: const ButtonStyle(visualDensity: VisualDensity.compact),
        segments: const [
          ButtonSegment(value: 4, label: Text('4h')),
          ButtonSegment(value: 8, label: Text('8h')),
          ButtonSegment(value: 12, label: Text('12h')),
        ],
        selected: {hours},
        onSelectionChanged: (s) => ref.read(crewTipHoursProvider.notifier).state = s.first,
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        if (data.assistant == null)
          const Text('Asystent chwilowo niedostępny.', style: TextStyle(color: AppColors.textSecondary)),
        if (data.assistant != null && tips.isEmpty)
          const Text('Brak wolnych NPC gotowych do pracy — wszyscy pracują albo odpoczywają.',
              style: TextStyle(color: AppColors.textSecondary)),
        for (var i = 0; i < tips.length; i++)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surfaceLight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: i == 0 ? AppColors.gold.withValues(alpha: 0.6) : AppColors.border),
            ),
            child: Wrap(
              spacing: 12,
              runSpacing: 8,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(minWidth: 180, maxWidth: 420),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${i + 1}. ${tips[i].npcName} → ${tips[i].serviceName}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    const SizedBox(height: 2),
                    Text(
                      '${tips[i].hours} h · ${tips[i].car == null ? 'autobus' : carName(tips[i].car)} · popyt ${(tips[i].demand * 100).round()}%'
                      '${tips[i].burnout ? ' · ⚠️ ryzyko przemęczenia' : ''}',
                      style: TextStyle(fontSize: 12, color: tips[i].burnout ? AppColors.warning : AppColors.textSecondary),
                    ),
                  ]),
                ),
                Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('≈ ${money(tips[i].cash)}', style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.success)),
                  const SizedBox(width: 10),
                  FilledButton.tonal(onPressed: () => onApply(tips[i]), child: const Text('Zastosuj Poradę')),
                ]),
              ],
            ),
          ),
        for (final a in alerts)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('⚠️ $a', style: const TextStyle(fontSize: 12.5, color: AppColors.warning)),
          ),
      ]),
    );
  }
}

class _RidesCard extends StatelessWidget {
  const _RidesCard({required this.data, required this.now});
  final CrewData data;
  final int now;
  @override
  Widget build(BuildContext context) {
    String kind(Ride r) => switch (r.kind) { 'taxi' => '🚕 Taxi', 'pickup' => '🏠 Odbiór ekipy', _ => '🚐 Dowóz do pracy' };
    return SectionCard(
      title: 'Kursy w toku (${data.rides.length})',
      icon: Icons.route_rounded,
      child: Column(children: [
        for (final r in data.rides)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 5),
            child: Row(children: [
              Expanded(child: Text('${kind(r)} · ${r.driverName} · ${carName(r.car)}${r.passengers.isEmpty ? '' : ' · ${r.passengers.length} pas.'}')),
              Text('do ${fmtClock(r.backAt)}', style: const TextStyle(color: AppColors.textSecondary)),
            ]),
          ),
      ]),
    );
  }
}

class _EmptyCrew extends StatelessWidget {
  const _EmptyCrew({required this.onRecruit});
  final VoidCallback onRecruit;
  @override
  Widget build(BuildContext context) {
    return SectionCard(
      title: 'Nie masz jeszcze ekipy',
      icon: Icons.group_add_rounded,
      child: Column(children: [
        const Text('Zatrudnij pierwszego pracownika w Dzielnicy Nadmorskiej. SERVICE zarabia w usługach, DRIVER rozwozi ekipę i jeździ na Taxi.',
            style: TextStyle(color: AppColors.textSecondary)),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: onRecruit, icon: const Icon(Icons.person_add_alt_1_rounded), label: const Text('+ Zrekrutuj Pracownika')),
      ]),
    );
  }
}
