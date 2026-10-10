import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../crew/crew_models.dart' show ServiceWork;
import '../crew/crew_providers.dart';
import '../crew/crew_sheets.dart';
import '../crew/npc_card.dart' show NpcAvatar;
import '../auth/auth_form.dart' show ErrorBanner;
import 'map_board.dart';
import 'map_layout.dart';
import 'map_providers.dart';
import 'map_widgets.dart';

/// Treść panelu lokacji (ta sama dla prawego panelu desktop i bottom sheetu mobile).
class MapPanelContent extends ConsumerWidget {
  const MapPanelContent({super.key, required this.sel, required this.d, this.scroll});
  final MapSelection sel;
  final MapData d;
  final ScrollController? scroll;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final close = IconButton(
      key: const Key('panel-close'),
      tooltip: 'Zamknij',
      onPressed: () => ref.read(mapSelectionProvider.notifier).state = null,
      icon: const Icon(Icons.close_rounded),
    );
    final body = switch (sel.kind) {
      MapSelKind.service => _ServiceBody(d: d, id: sel.id),
      MapSelKind.district => _DistrictBody(d: d, id: int.parse(sel.id)),
      MapSelKind.landmark => _LandmarkBody(lm: d.layout.landmarks.firstWhere((x) => x.id == sel.id)),
    };
    return ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(18, 6, 18, 24), children: [
      Align(alignment: Alignment.centerRight, child: close),
      body,
    ]);
  }
}

Widget _header(String icon, String title, String subtitle) => Row(children: [
      Container(
        width: 52,
        height: 52,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(14)),
        child: Text(icon, style: const TextStyle(fontSize: 28)),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
          Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ]),
      ),
    ]);

Widget _section(String t) => Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Text(t.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
    );

String _countdown(int ms) {
  final s = (ms / 1000).floor().clamp(0, 1 << 30);
  final h = s ~/ 3600, m = (s % 3600) ~/ 60, sec = s % 60;
  return h > 0 ? '$h h ${m.toString().padLeft(2, '0')} min' : '$m min ${sec.toString().padLeft(2, '0')} s';
}

// ───────────────────────────── usługa
class _ServiceBody extends ConsumerStatefulWidget {
  const _ServiceBody({required this.d, required this.id});
  final MapData d;
  final String id;
  @override
  ConsumerState<_ServiceBody> createState() => _ServiceBodyState();
}

class _ServiceBodyState extends ConsumerState<_ServiceBody> {
  Timer? _t;
  bool _busy = false;
  final _completed = <String>{};
  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() {});
      final works = ref.read(crewProvider).valueOrNull?.worksAt(widget.id) ?? const <ServiceWork>[];
      var ended = false;
      for (final work in works) {
        if (work.endsAt <= widget.d.nowMs && _completed.add('${work.npc.id}:${work.endsAt}')) ended = true;
      }
      // Po końcu zmiany serwer rozlicza pracownika; nie zostawiamy wiecznego „kończy zmianę”.
      if (ended || timer.tick % 30 == 0) ref.invalidate(crewProvider);
    });
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final s = d.service(widget.id);
    final slot = d.layout.slot(widget.id);
    if (s == null || slot == null) return const Text('Brak danych lokacji.');
    final m = d.layout.district(s.district);
    final now = d.nowMs;
    final left = d.changesAt - now;
    final works = ref.watch(crewProvider).valueOrNull?.worksAt(s.id) ?? const <ServiceWork>[];
    Widget demandBox(String label, int pct, String sub) => Expanded(
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: demandColor(pct).withValues(alpha: .10),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: demandColor(pct).withValues(alpha: .45)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              const SizedBox(height: 4),
              Text('${demandBadge(pct)} $pct%', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: demandColor(pct))),
              Text(sub, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            ]),
          ),
        );
    final nextRate = s.rateNow / (s.demand == 0 ? 1 : s.demand) * s.demandNextPct / 100;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _header(s.icon, s.name, '${m.icon} ${m.name}${s.unlocked ? '' : ' · 🔒 zablokowana'}'),
      const SizedBox(height: 12),
      Text(slot.desc, style: const TextStyle(color: AppColors.textSecondary, height: 1.4)),
      _section('Popyt'),
      Row(children: [
        demandBox('Teraz', s.demandPct, '${money(s.rateNow)}/h'),
        const SizedBox(width: 10),
        demandBox('Następne okno', s.demandNextPct, '~${money(nextRate)}/h'),
      ]),
      const SizedBox(height: 6),
      Text(left > 0 ? '⏱️ Zmiana popytu za ${_countdown(left)}' : '⏱️ Popyt właśnie się zmienia…',
          key: const Key('panel-countdown'), style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      _section('Akcje'),
      if (!s.unlocked)
        Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: OutlinedButton.icon(
            key: const Key('panel-unlock'),
            onPressed: !s.canUnlock || _busy
                ? null
                : () async {
                    setState(() => _busy = true);
                    final r = await ref.read(mapActionsProvider).unlock(s.id);
                    if (!context.mounted) return;
                    setState(() => _busy = false);
                    showMapResult(context, r);
                  },
            icon: const Icon(Icons.lock_open_rounded),
            label: Text('Odblokuj · ${money(s.unlockCost)} (od lvl ${s.levelReq})'),
          ),
        ),
      // M4: kto tu pracuje — awatar, pasek postępu zmiany, pozostały czas; nikt → przycisk wysyłki jak dotąd
      if (works.isNotEmpty) ...[
        for (final w in works) _WorkCard(w: w, now: now),
        const SizedBox(height: 4),
        OutlinedButton.icon(
          key: const Key('panel-send-npc'),
          onPressed: s.unlocked ? () => showCrewModal(context, NpcPickSheet(serviceId: s.id, serviceName: s.name)) : null,
          icon: const Text('👷', style: TextStyle(fontSize: 18)),
          label: const Text('Wyślij kolejnego NPC'),
          style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(44)),
        ),
      ] else
        FilledButton.icon(
          key: const Key('panel-send-npc'),
          onPressed: s.unlocked ? () => showCrewModal(context, NpcPickSheet(serviceId: s.id, serviceName: s.name)) : null,
          icon: const Text('👷', style: TextStyle(fontSize: 18)),
          label: const Text('Wyślij NPC do pracy'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
        ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        key: const Key('panel-travel'),
        onPressed: d.here == s.district ? null : () => showCrewModal(context, TravelSheet(target: s.district)),
        icon: const Text('🧭', style: TextStyle(fontSize: 18)),
        label: Text(d.here == s.district ? 'Jesteś w tej dzielnicy' : 'Jedź tutaj (${m.name})'),
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)),
      ),
    ]);
  }
}

// ───────────────────────────── dzielnica
class _DistrictBody extends ConsumerWidget {
  const _DistrictBody({required this.d, required this.id});
  final MapData d;
  final int id;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final m = d.layout.district(id);
    final region = d.layout.regionOf(m);
    final here = d.here == id;
    final open = d.isOpen(id);
    final kind = switch (m.kind) { 'city' => 'miasto', 'resource' => 'lokacja surowcowa', _ => 'strefa specjalna' };
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      _header(m.icon, m.name, '${region?.name ?? ''} · $kind'),
      const SizedBox(height: 10),
      if (here)
        const Text('📍 TU JESTEŚ', style: TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900))
      else if (!open)
        const Text('🔒 Dzielnica otworzy się w kolejnej Erze świata.', style: TextStyle(color: AppColors.textSecondary)),
      _section('Lokacje usługowe'),
      if (d.servicesIn(id).isEmpty) const Text('Brak usług w tej dzielnicy.', style: TextStyle(color: AppColors.textSecondary)),
      for (final s in d.servicesIn(id))
        Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            key: Key('panel-svc-${s.id}'),
            leading: Text(s.unlocked ? s.icon : '🔒', style: const TextStyle(fontSize: 22)),
            title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('${demandBadge(s.demandPct)} ${s.demandPct}% · ${money(s.rateNow)}/h',
                style: TextStyle(color: demandColor(s.demandPct), fontWeight: FontWeight.w700)),
            trailing: const Icon(Icons.chevron_right_rounded),
            onTap: () => ref.read(mapSelectionProvider.notifier).state = MapSelection(MapSelKind.service, s.id),
          ),
        ),
      const SizedBox(height: 10),
      FilledButton.icon(
        key: const Key('panel-travel'),
        onPressed: here || !open ? null : () => showCrewModal(context, TravelSheet(target: id)),
        icon: const Text('🧭', style: TextStyle(fontSize: 18)),
        label: Text(here ? 'Jesteś tutaj' : 'Jedź tutaj'),
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
      ),
    ]);
  }
}

class _LandmarkBody extends StatelessWidget {
  const _LandmarkBody({required this.lm});
  final MapLandmark lm;
  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        _header(lm.icon, lm.name, 'Wyspa · wkrótce'),
        const SizedBox(height: 12),
        Text(lm.note, style: const TextStyle(color: AppColors.textSecondary, height: 1.4)),
      ]);
}

// ───────────────────────────── szybki wybór wolnego NPC → istniejący DispatchSheet (zmiana 2/4/8/12 h)
class NpcPickSheet extends ConsumerWidget {
  const NpcPickSheet({super.key, required this.serviceId, required this.serviceName});
  final String serviceId, serviceName;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(crewProvider);
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 24),
      child: async.when(
        loading: () => const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
        error: (e, _) => ErrorBanner('$e'),
        data: (data) {
          final free = data.npcs.where((n) => !n.busy && !n.isDriver).toList();
          return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('👷 Kogo wysłać: $serviceName?', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 4),
            const Text('Wolni pracownicy. Kierowcy dowiozą ich w tle.', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            const SizedBox(height: 12),
            if (free.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Text('Wszyscy pracownicy są zajęci. Zatrudnij kogoś w zakładce Ekipa.', textAlign: TextAlign.center),
              ),
            for (final n in free)
              Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  key: Key('pick-npc-${n.id}'),
                  leading: NpcAvatar(n, size: 38),
                  title: Text(n.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('⚡ ${n.energy.round()} · 🙂 ${n.mood.round()} · 🍽️ ${n.satiety.round()}${n.exhausted ? ' · 😡 wypalony' : ''}'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () {
                    final nav = Navigator.of(context);
                    nav.pop();
                    showCrewModal(nav.context, DispatchSheet(npc: n, data: data, initialService: serviceId));
                  },
                ),
              ),
          ]);
        },
      ),
    );
  }
}

/// M4: karta pracownika w usłudze.
class _WorkCard extends StatelessWidget {
  const _WorkCard({required this.w, required this.now});
  final ServiceWork w;
  final int now;
  @override
  Widget build(BuildContext context) {
    final left = w.left(now);
    final h = left ~/ 3600000, m = (left % 3600000) ~/ 60000, sec = (left % 60000) ~/ 1000;
    final txt = left <= 0 ? 'kończy zmianę…' : (h > 0 ? 'zostało $h h ${m.toString().padLeft(2, '0')} min' : 'zostało $m min ${sec.toString().padLeft(2, '0')} s');
    return Container(
      key: Key('work-${w.npc.id}'),
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.success.withValues(alpha: .08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.success.withValues(alpha: .35)),
      ),
      child: Row(children: [
        NpcAvatar(w.npc, size: 44),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(w.npc.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800)),
            Text(txt, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.success)),
            const SizedBox(height: 2),
            Text(w.phaseLabel, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                key: const Key('work-progress'),
                value: w.progress(now),
                minHeight: 7,
                backgroundColor: AppColors.border,
                valueColor: const AlwaysStoppedAnimation(AppColors.success),
              ),
            ),
          ]),
        ),
      ]),
    );
  }
}
