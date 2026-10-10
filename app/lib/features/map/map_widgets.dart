import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'map_providers.dart';

// Elementy mapy z wersji przed UI v2 (bez zmian logiki): odznaki popytu, pasek asystenta, baner podróży, okno podróży.
String demandBadge(int pct) => pct >= 115 ? '🔥' : (pct < 85 ? '📉' : '•');
Color demandColor(int pct) => pct >= 115 ? AppColors.success : (pct < 85 ? AppColors.danger : AppColors.warning);

/// Pasek asystenta podróży: najlepsze lokacje dzisiaj + pierwsza porada.
class AssistantBar extends StatefulWidget {
  const AssistantBar({super.key, required this.d, required this.now, this.compact = false});
  final MapData d;
  final int now;
  /// Telefon: jedna linia, porada po dotknięciu (mapa zostaje widoczna).
  final bool compact;
  @override
  State<AssistantBar> createState() => _AssistantBarState();
}

class _AssistantBarState extends State<AssistantBar> {
  bool _open = false;
  @override
  Widget build(BuildContext context) {
    final d = widget.d, now = widget.now;
    if (widget.compact && !_open) {
      final top3 = d.demandTop.take(3).map((t) => '${t['icon'] ?? ''} ${((t['demand'] as num? ?? 1) * 100).round()}%').join('  ');
      return Material(
        color: AppColors.surface.withValues(alpha: .95),
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          key: const Key('map-assistant'),
          borderRadius: BorderRadius.circular(12),
          onTap: () => setState(() => _open = true),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.primary.withValues(alpha: .4))),
            child: Row(children: [
              Expanded(child: Text('💡 Top trasy: $top3', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13))),
              const Icon(Icons.expand_more_rounded, size: 18, color: AppColors.textSecondary),
            ]),
          ),
        ),
      );
    }
    final top = d.demandTop.map((t) => '${t['name']} (${((t['demand'] as num? ?? 1) * 100).round()}%)').join(', ');
    final mins = d.changesAt > now ? ((d.changesAt - now) / 60000).ceil() : 0;
    return GestureDetector(
      onTap: widget.compact ? () => setState(() => _open = false) : null,
      child: Container(
      key: const Key('map-assistant'),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [Color.alphaBlend(AppColors.primary.withValues(alpha: .18), AppColors.surface), AppColors.surface]),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.primary.withValues(alpha: .4)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('💡 Najlepsze trasy dzisiaj: $top', style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text(
          d.tips.isNotEmpty ? d.tips.first : 'Popyt zmienia się co 6 h${mins > 0 ? ' — następna zmiana za $mins min' : ''}.',
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
      ]),
    ));
  }
}

/// Baner trwającej podróży z odliczaniem i przyciskiem przyjazdu.
class TravelBanner extends ConsumerWidget {
  const TravelBanner({required this.d, required this.now});
  final MapData d;
  final int now;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = d.travel!;
    final until = (t['until'] as num?)?.toInt() ?? now;
    final started = (t['started'] as num?)?.toInt() ?? now;
    final left = math.max(0, until - now);
    final total = math.max(1, until - started);
    final icon = switch (t['mode']) { 'car' => '🚗', 'hitchhike' => '👍', _ => '🚌' };
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('$icon W drodze do: ${t['toName']}', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          MeterBar(value: 1 - left / total, color: AppColors.primary, height: 8),
          const SizedBox(height: 8),
          if (left > 0)
            Text('Na miejscu za ${_fmt(left)}', style: const TextStyle(color: AppColors.textSecondary))
          else
            FilledButton(
              key: const Key('travel-arrive'),
              onPressed: () async {
                final r = await ref.read(mapActionsProvider).arrive();
                if (context.mounted) showMapResult(context, r);
              },
              child: const Text('📍 JESTEM NA MIEJSCU'),
            ),
        ]),
      ),
    );
  }
}

String _fmt(int ms) {
  final s = (ms / 1000).ceil();
  return s >= 60 ? '${s ~/ 60} min ${s % 60} s' : '$s s';
}


// Modal podróży: bus / auto z garażu / autostop → POST /travel
// ---------------------------------------------------------------------------
class TravelSheet extends ConsumerStatefulWidget {
  const TravelSheet({super.key, required this.target});
  final int target;
  @override
  ConsumerState<TravelSheet> createState() => _TravelSheetState();
}

class _TravelSheetState extends ConsumerState<TravelSheet> {
  String _mode = 'bus';
  bool _busy = false;

  @override
  Widget build(BuildContext context) {
    final d = ref.watch(mapProvider).valueOrNull;
    if (d == null) return const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()));
    final m = d.layout.district(widget.target);
    final dist = (widget.target - d.here).abs();
    // czasy jak w travel.travel_ms (ms realne): bus 5 min × odległość / tempo świata (min 60 s), auto 20%
    final busMs = math.max(60000, (5 * dist * 60000 / d.speed).round());
    final carMs = math.max(1000, (busMs * 0.2).round());
    final hitchMin = math.max(1000, (3 * 60000 / d.speed).round()), hitchMax = math.max(1000, (10 * 60000 / d.speed).round());
    final car = d.district.fleet.where((c) => c.active).firstOrNull;
    final need = car == null ? 0 : math.max(1, dist) * car.fuelPerHop;
    final carProblem = car == null
        ? 'Brak wybranego auta — kup lub wybierz auto w Garażu.'
        : (car.wear >= 100
            ? 'Auto zużyte w 100% — serwisuj w Garażu.'
            : (car.fuel + 1e-9 < need ? '⛽ Za mało paliwa! (${car.fuel.round()}%, potrzeba $need%) Zatankuj w Garażu.' : null));
    final here = dist == 0;
    final blocked = here ? 'Już jesteś w tej dzielnicy.' : (!d.isOpen(m.id) ? 'Dzielnica niedostępna w obecnej Erze świata.' : (d.travel != null ? 'Jesteś już w drodze.' : null));
    final canGo = blocked == null && !_busy && !(_mode == 'car' && carProblem != null) && !(_mode == 'bus' && d.district.cash < 20);

    Widget option(String id, String icon, String title, String cost, String time, {String? warn, String? note}) {
      final sel = _mode == id;
      return GestureDetector(
        key: Key('mode-$id'),
        onTap: () => setState(() => _mode = id),
        child: Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: sel ? AppColors.primary.withValues(alpha: .12) : AppColors.surfaceLight,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: sel ? AppColors.primary : AppColors.border, width: sel ? 2 : 1),
          ),
          child: Row(children: [
            Text(icon, style: const TextStyle(fontSize: 26)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                Text('$cost · $time', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                if (note != null) Text(note, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                if (warn != null) Text(warn, style: const TextStyle(fontSize: 12, color: AppColors.warning, fontWeight: FontWeight.w700)),
              ]),
            ),
            Icon(sel ? Icons.radio_button_checked : Icons.radio_button_off, color: sel ? AppColors.primary : AppColors.textSecondary),
          ]),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Text(m.icon, style: const TextStyle(fontSize: 28)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(m.name, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
              Text(here ? 'Tu jesteś' : '$dist przyst. od Twojej lokalizacji', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            ]),
          ),
          IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
        ]),
        for (final s in d.servicesIn(m.id))
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('${s.icon} ${s.name}: ${demandBadge(s.demandPct)} ${s.demandPct}% popytu · ${money(s.rateNow)}/h',
                style: TextStyle(fontSize: 13, color: demandColor(s.demandPct))),
          ),
        const SizedBox(height: 14),
        if (blocked != null)
          Padding(padding: const EdgeInsets.only(bottom: 10), child: Text(blocked, style: const TextStyle(color: AppColors.warning)))
        else ...[
          option('bus', '🚌', 'Autobus', '20 \$', _fmt(busMs), warn: d.district.cash < 20 ? 'Brakuje gotówki na bilet.' : null),
          option('car', '🚗', car == null ? 'Auto z Garażu' : 'Auto: ${car.name}', '0 \$ · ⛽ −$need%', '${_fmt(carMs)} (−80%)', warn: carProblem),
          option('hitchhike', '👍', 'Autostop', '0 \$', '${_fmt(hitchMin)}–${_fmt(hitchMax)} (losowo)', note: '15% ryzyka utraty 10 energii'),
        ],
        const SizedBox(height: 8),
        FilledButton(
          key: const Key('travel-go'),
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          onPressed: canGo
              ? () async {
                  setState(() => _busy = true);
                  final r = await ref.read(mapActionsProvider).travel(widget.target, _mode);
                  if (!context.mounted) return;
                  setState(() => _busy = false);
                  if (r.ok) Navigator.pop(context);
                  showMapResult(context, r);
                }
              : null,
          child: Text(_busy ? 'Ruszam…' : '🧭 RUSZAJ W DROGĘ', style: const TextStyle(fontWeight: FontWeight.w900)),
        ),
      ]),
    );
  }
}

void showMapResult(BuildContext context, MapResult r) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(r.message),
      backgroundColor: r.ok ? AppColors.surfaceLight : AppColors.danger.withValues(alpha: 0.9),
      behavior: SnackBarBehavior.floating,
    ));
}
