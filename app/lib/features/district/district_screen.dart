import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart';
import '../crew/crew_sheets.dart' show showCrewModal;
import 'district_providers.dart';
import 'district_visual.dart';
import 'district_sheets.dart';

/// Ekran „Dzielnica” (GDD v3.1, etap 4): 6 budynków, skarbce idle, Buffet, Sala Chwały.
/// Plan dzielnicy; szczegóły tylko w panelu klikniętego budynku.
class DistrictScreen extends ConsumerStatefulWidget {
  const DistrictScreen({super.key});
  @override
  ConsumerState<DistrictScreen> createState() => _DistrictScreenState();
}

class _DistrictScreenState extends ConsumerState<DistrictScreen> {
  Timer? _poll;

  /// M5: klik w budynek na planie → panel z jego szczegółami (jak na mapie), bez przewijania w dół.
  void _onObject(String id) => showBuildingPanel(context, id);

  @override
  void initState() {
    super.initState();
    // skarbce rosną w czasie — odświeżanie co 30 s
    _poll = Timer.periodic(const Duration(seconds: 30), (_) => ref.invalidate(districtProvider));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(districtProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(districtProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
      ),
      data: (d) => RefreshIndicator(
        onRefresh: () => ref.refresh(districtProvider.future),
        child: LayoutBuilder(builder: (context, c) {
          final pad = c.maxWidth >= 600 ? 24.0 : 12.0;
          return ListView(
            padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 70),
            children: [
              Row(children: [
                const Expanded(child: Text('Moja dzielnica', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(20), border: Border.all(color: AppColors.border)),
                  child: Text(money(d.cash), style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.success)),
                ),
              ]),
              if (d.prestigeBonus > 0)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('🏆 Bonus resetu: +${d.prestigeBonus}% do odbiorów skarbców',
                      style: const TextStyle(color: AppColors.gold, fontSize: 12)),
                ),
              const SizedBox(height: 14),
              DistrictVisual(d: d, onTap: _onObject),
              const SizedBox(height: 10),
              // M5: szczegóły budynków tylko w panelu po kliknięciu
              Row(children: [
                const Icon(Icons.touch_app_rounded, size: 16, color: AppColors.textSecondary),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    d.construction == null
                        ? 'Kliknij budynek, aby zobaczyć szczegóły, rozbudować lub odebrać skarbiec.'
                        : 'Trwa budowa: ${d.byId(d.construction!.building).name} → poziom ${d.construction!.target}. Kliknij budynek, aby zobaczyć szczegóły.',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                  ),
                ),
              ]),
            ],
          );
        }),
      ),
    );
  }
}

/// M5: panel budynku otwierany kliknięciem na planie — okno (desktop) albo arkusz od dołu (telefon).
Future<void> showBuildingPanel(BuildContext context, String id) {
  final wide = MediaQuery.sizeOf(context).width >= 600;
  if (wide) {
    return showDialog(
      context: context,
      barrierColor: Colors.black54,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(24),
        child: ConstrainedBox(constraints: BoxConstraints(maxWidth: 420, maxHeight: MediaQuery.sizeOf(context).height * .85), child: SingleChildScrollView(child: BuildingPanel(id: id))),
      ),
    );
  }
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => SafeArea(child: Padding(padding: const EdgeInsets.fromLTRB(10, 0, 10, 10), child: ConstrainedBox(constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * .85), child: SingleChildScrollView(child: BuildingPanel(id: id))))),
  );
}

/// Zawartość panelu: żywe dane (odświeżają się po akcji), własny stan „busy”.
class BuildingPanel extends ConsumerStatefulWidget {
  const BuildingPanel({super.key, required this.id});
  final String id;
  @override
  ConsumerState<BuildingPanel> createState() => _BuildingPanelState();
}

class _BuildingPanelState extends ConsumerState<BuildingPanel> {
  final _busy = <String>{};

  Future<void> _act(String key, Future<DistrictResult> Function() action) async {
    if (_busy.contains(key)) return;
    setState(() => _busy.add(key));
    try {
      final r = await action();
      if (mounted) showDistrictResult(context, r);
    } catch (_) {
      if (mounted) showDistrictResult(context, const DistrictResult('Nie udało się wykonać akcji. Odśwież dane i spróbuj ponownie.', ok: false));
    } finally {
      if (mounted) setState(() => _busy.remove(key));
    }
  }

  /// Zamyka panel i przechodzi gdzie indziej (Klub, Ekipa).
  void _go(String route, {Object? extra}) {
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    router.go(route, extra: extra);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(districtProvider);
    if (state.hasError) {
      return Card(child: Padding(padding: const EdgeInsets.all(20), child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Nie udało się pobrać szczegółów budynku.'),
        const SizedBox(height: 12),
        FilledButton(onPressed: () => ref.invalidate(districtProvider), child: const Text('Spróbuj ponownie')),
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Zamknij')),
      ])));
    }
    final d = state.valueOrNull;
    if (d == null) return Card(child: Padding(padding: const EdgeInsets.all(30), child: Column(mainAxisSize: MainAxisSize.min, children: [
      const CircularProgressIndicator(),
      TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Zamknij')),
    ])));
    final b = d.byId(widget.id);
    final a = ref.read(districtActionsProvider);
    final cons = d.construction;
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Stack(children: [
        BuildingCard(
          key: Key('panel-${b.id}'),
          b: b,
          d: d,
          busy: _busy,
          onUpgrade: () => _act('up-${b.id}', () => a.upgrade(b.id)),
          onCollect: b.id == 'cafe'
              ? () => _act('col-cafe', a.collectCafe)
              : (b.id == 'nightclub' ? () => _act('col-nightclub', a.collectNightclub) : null),
          onOpen: switch (b.id) {
            'residence' => () => showCrewModal(context, const BuffetSheet()),
            'garage' => () => showCrewModal(context, const FleetSheet()),
            'club' => () => _go('/club', extra: 'enter'),
            'hall' => d.hallOpen ? () => showCrewModal(context, const HallSheet()) : null,
            _ => null,
          },
          onCrew: b.id == 'residence' ? () => _go('/crew') : null,
          construction: cons,
        ),
        Positioned(
          right: 4,
          top: 4,
          child: IconButton(
            key: const Key('panel-close'),
            tooltip: 'Zamknij',
            icon: const Icon(Icons.close_rounded),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ),
      ]),
    ]);
  }
}

/// Karta jednego budynku.
class BuildingCard extends StatelessWidget {
  const BuildingCard({
    super.key,
    required this.b,
    required this.d,
    required this.busy,
    required this.onUpgrade,
    this.onCollect,
    this.onOpen,
    this.onCrew,
    this.compact = false,
    this.construction,
  });
  final Construction? construction; // M5: trwająca budowa (dowolnego budynku)
  final Building b;
  final DistrictData d;
  final Set<String> busy;
  final VoidCallback onUpgrade;
  final VoidCallback? onCollect, onOpen, onCrew;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final small = const TextStyle(fontSize: 12, color: AppColors.textSecondary);
    final body = <Widget>[];
    switch (b.id) {
      case 'residence':
        const meals = ['brak', 'Zwykły', 'Dobre jedzenie', 'Premium catering'];
        if (d.npcs.isNotEmpty) body.add(Text('👥 NPC: ${d.npcCount}/${d.npcSlots}', style: small));
        body.add(Text('🍽️ Buffet: ${d.buffet}/3 · ${meals[d.buffet]}', style: small));
        body.add(const SizedBox(height: 8));
        body.add(Wrap(spacing: 6, runSpacing: 6, children: [
          _SmallBtn(key: const Key('res-crew'), label: 'Ekipa / Sen', icon: Icons.bedtime_rounded, onTap: onCrew),
          _SmallBtn(key: const Key('res-buffet'), label: 'Buffet', icon: Icons.restaurant_rounded, onTap: onOpen),
        ]));
      case 'garage':
        final cars = d.cars;
        final avg = cars.isEmpty ? 0.0 : cars.map((c) => c.$2).reduce((a, b) => a + b) / cars.length;
        body.add(Text('🚘 Auta: ${cars.length}/5', style: small));
        final lowFuel = d.fleet.where((c) => c.fuel < 30).length;
        if (lowFuel > 0) body.add(Text('⛽ Mało paliwa: $lowFuel', style: small.copyWith(color: AppColors.warning)));
        if (cars.isNotEmpty) {
          body.add(const SizedBox(height: 6));
          body.add(MeterBar(value: avg / 100, color: _wearColor(avg), label: 'Średnie zużycie ${avg.round()}%'));
          if (!compact) {
            body.add(const SizedBox(height: 6));
            for (final c in cars.take(3)) {
              body.add(Text('${d.carName(c.$1)} · ${c.$2.round()}%', style: small, overflow: TextOverflow.ellipsis));
            }
          }
        } else {
          body.add(Text('Kup auto w salonie', style: small));
        }
        body.add(const SizedBox(height: 8));
        body.add(_SmallBtn(key: const Key('garage-fleet'), label: 'Flota', icon: Icons.local_gas_station_rounded, onTap: onOpen));
      case 'cafe' || 'nightclub':
        final v = d.vault(b.id);
        if (v == null) {
          body.add(Text('Nie wybudowano. Skarbiec ${b.id == 'cafe' ? 24 : 72} h.', style: small));
        } else {
          body.add(VaultMeter(key: Key('vault-bar-${b.id}'), v: v));
          body.add(const SizedBox(height: 6));
          body.add(Text(money(v.amount.floor()), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppColors.success)));
          body.add(Text(v.fill >= 1 ? 'PEŁNY — produkcja stoi!' : '${money(v.ratePerHour)}/h · pełny za ${_hours(v.hoursToFull)}',
              style: small.copyWith(color: v.fill >= 1 ? AppColors.gold : null, fontWeight: v.fill >= 1 ? FontWeight.w800 : null)));
          body.add(const SizedBox(height: 8));
          final k = 'col-${b.id}';
          body.add(FilledButton(
            key: Key('collect-${b.id}'),
            style: FilledButton.styleFrom(backgroundColor: AppColors.gold, foregroundColor: Colors.black, minimumSize: const Size.fromHeight(38)),
            onPressed: busy.contains(k) || v.amount < 1 ? null : onCollect,
            child: FittedBox(child: Text(busy.contains(k) ? '…' : '💰 ODBIERZ SKARBIEC', style: const TextStyle(fontWeight: FontWeight.w800))),
          ));
        }
      case 'club':
        body.add(Text('Hub dyscyplin: walki, siłownia, lochy.', style: small));
        body.add(const SizedBox(height: 8));
        body.add(_SmallBtn(key: const Key('club-enter'), label: 'Wejdź', icon: Icons.login_rounded, onTap: onOpen));
      case 'hall':
        if (d.hallOpen) {
          body.add(Text('Odblokowana · Reset #${d.resets + 1} dostępny', style: small.copyWith(color: AppColors.gold)));
          body.add(const SizedBox(height: 8));
          body.add(_SmallBtn(key: const Key('hall-enter'), label: 'Wejdź', icon: Icons.emoji_events_rounded, onTap: onOpen));
        } else {
          final miss = d.hallMissing;
          final done = DistrictData.hallRequires.length - miss.length;
          body.add(MeterBar(value: done / DistrictData.hallRequires.length, color: AppColors.gold, label: '🔒 Max budynków $done/5 + ${money(d.hallCost)}'));
          if (!compact && miss.isNotEmpty) {
            body.add(const SizedBox(height: 6));
            body.add(Text('Brakuje: ${miss.map((m) => '${m.name} ${m.level}/${m.max}').join(', ')}', style: small, maxLines: 3, overflow: TextOverflow.ellipsis));
          }
        }
    }

    final up = _upgradeButton(context);
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: EdgeInsets.all(compact ? 10 : 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(b.icon, style: TextStyle(fontSize: compact ? 22 : 28)),
            const SizedBox(width: 8),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(b.name, style: TextStyle(fontWeight: FontWeight.w800, fontSize: compact ? 14 : 16), overflow: TextOverflow.ellipsis),
                Text(b.built ? 'Lvl ${b.level}/${b.max}' : (b.id == 'hall' ? '🔒 Zablokowana' : 'Nie wybudowano'),
                    style: TextStyle(fontSize: 12, color: b.maxed ? AppColors.gold : AppColors.primary, fontWeight: FontWeight.w700)),
              ]),
            ),
          ]),
          const SizedBox(height: 10),
          ...body,
          if (up != null) ...[const SizedBox(height: 8), up],
        ]),
      ),
    );
  }

  Widget? _upgradeButton(BuildContext context) {
    final c = construction;
    // M5: ten budynek się buduje → pasek postępu zamiast przycisku
    if (c != null && c.building == b.id) return ConstructionPill(c: c, wide: true);
    if (b.id == 'club') return null; // Sala Klubowa ma tylko poziom 1
    if (b.id == 'hall' && d.hallOpen) return null;
    if (b.maxed) {
      return const Text('✔ Poziom maksymalny', textAlign: TextAlign.center, style: TextStyle(color: AppColors.gold, fontSize: 12, fontWeight: FontWeight.w700));
    }
    final cost = b.nextCost ?? 0;
    final canAfford = d.cash >= cost;
    final hallLocked = b.id == 'hall' && d.hallMissing.isNotEmpty;
    final label = b.id == 'hall'
        ? 'Odblokuj (${money(cost)})'
        : (b.built ? 'Rozbuduj do Lvl ${b.level + 1} (${money(cost)})' : 'Wybuduj (${money(cost)})');
    final k = 'up-${b.id}';
    // M5: jedna budowa naraz — inny budynek w budowie blokuje przycisk
    if (c != null) {
      return OutlinedButton(
        key: Key('upgrade-${b.id}'),
        style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(36), padding: const EdgeInsets.symmetric(horizontal: 8)),
        onPressed: null,
        child: FittedBox(child: Text('🏗️ Trwa budowa: ${d.byId(c.building).name} (${fmtLeft(c.left())})')),
      );
    }
    final time = b.id == 'hall' ? 'Budowa ${fmtLeft(Duration(seconds: (28800 / d.speed).floor()))}' : 'Budowa ${_buildTime(b)}';
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      OutlinedButton(
      key: Key('upgrade-${b.id}'),
      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(36), padding: const EdgeInsets.symmetric(horizontal: 8)),
      onPressed: busy.contains(k) || !canAfford || hallLocked ? null : onUpgrade,
      child: FittedBox(child: Text(busy.contains(k) ? '…' : label)),
    ),
      const SizedBox(height: 4),
      Text('⏱ $time', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
    ]);
  }

  /// Czas budowy jak w backendzie (economy.build_seconds): 5 min → 4 h wykładniczo; dzielony przez tempo świata.
  String _buildTime(Building b) {
    final target = b.level + 1;
    final f = b.max <= 1 ? 0.0 : ((target - 1) / (b.max - 1)).clamp(0.0, 1.0);
    final secs = (300 * math.pow(14400 / 300, f)).round() / d.speed;
    return fmtLeft(Duration(seconds: math.max(1, secs.floor())));
  }
}

class _SmallBtn extends StatelessWidget {
  const _SmallBtn({super.key, required this.label, required this.icon, this.onTap});
  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => FilledButton.tonalIcon(
        style: FilledButton.styleFrom(visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 10)),
        onPressed: onTap,
        icon: Icon(icon, size: 16),
        label: Text(label, style: const TextStyle(fontSize: 12)),
      );
}

Color _wearColor(double w) => w < 30 ? AppColors.success : (w < 60 ? AppColors.warning : AppColors.danger);

String _hours(double h) => h >= 1 ? '${h.floor()} h ${((h % 1) * 60).round()} min' : '${(h * 60).ceil()} min';

void showDistrictResult(BuildContext context, DistrictResult r) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(r.message),
      backgroundColor: r.ok ? AppColors.surfaceLight : AppColors.danger.withValues(alpha: 0.9),
      behavior: SnackBarBehavior.floating,
    ));
}


/// Pasek skarbca: pełny (100%) = złoty i pulsujący — „Odbierz!”.
class VaultMeter extends StatefulWidget {
  const VaultMeter({super.key, required this.v});
  final Vault v;
  @override
  State<VaultMeter> createState() => _VaultMeterState();
}

class _VaultMeterState extends State<VaultMeter> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(covariant VaultMeter old) {
    super.didUpdateWidget(old);
    _sync();
  }

  void _sync() {
    final full = widget.v.fill >= 1;
    if (full && !_c.isAnimating) _c.repeat(reverse: true);
    if (!full && _c.isAnimating) _c.stop();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final v = widget.v;
    final full = v.fill >= 1;
    final label = full ? '💰 PEŁNY · Odbierz! · ${v.hours} h' : 'Skarbiec ${v.hours} h · ${(v.fill * 100).round()}%';
    if (!full) return MeterBar(value: v.fill, height: 8, color: AppColors.success, label: label);
    return AnimatedBuilder(
      animation: _c,
      builder: (_, child) => Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          boxShadow: [BoxShadow(color: AppColors.gold.withValues(alpha: .25 + .45 * _c.value), blurRadius: 6 + 10 * _c.value)],
        ),
        child: Transform.scale(scale: 1 + .02 * _c.value, child: child),
      ),
      child: MeterBar(value: 1, height: 8, color: AppColors.gold, label: label),
    );
  }
}
