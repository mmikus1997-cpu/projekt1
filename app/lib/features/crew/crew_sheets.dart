// ignore_for_file: sort_child_properties_last
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'crew_models.dart';
import 'crew_providers.dart';
import 'npc_card.dart';

/// Wspólny szkielet modala: bottom sheet na mobile, dialog (max 560 px) na tablet/desktop.
Future<T?> showCrewModal<T>(BuildContext context, Widget child) {
  final wide = MediaQuery.sizeOf(context).width >= 600;
  if (wide) {
    return showDialog<T>(
      context: context,
      builder: (_) => Dialog(
        backgroundColor: AppColors.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: AppColors.border)),
        child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 560, maxHeight: 720), child: child),
      ),
    );
  }
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
    builder: (_) => ConstrainedBox(constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.9), child: child),
  );
}

void showCrewResult(BuildContext context, CrewResult r) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(
      content: Text(r.message),
      backgroundColor: r.ok ? AppColors.surfaceLight : AppColors.danger.withValues(alpha: 0.9),
      behavior: SnackBarBehavior.floating,
    ));
}

class _ModalFrame extends StatelessWidget {
  const _ModalFrame({required this.title, this.leading, required this.children, required this.action});
  final String title;
  final Widget? leading;
  final List<Widget> children;
  final Widget action;
  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 8, 8),
        child: Row(children: [
          if (leading != null) ...[leading!, const SizedBox(width: 12)],
          Expanded(child: Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
          IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
        ]),
      ),
      const Divider(height: 1, color: AppColors.border),
      Flexible(
        child: ListView(shrinkWrap: true, padding: const EdgeInsets.fromLTRB(20, 14, 20, 8), children: children),
      ),
      Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 18), child: action),
    ]);
  }
}

Widget _label(String s) => Padding(
      padding: const EdgeInsets.only(top: 10, bottom: 8),
      child: Text(s.toUpperCase(),
          style: const TextStyle(fontSize: 11.5, letterSpacing: 1.1, fontWeight: FontWeight.w800, color: AppColors.textSecondary)),
    );

Widget _bigButton(String text, {required VoidCallback? onPressed, bool busy = false, Color? color}) => SizedBox(
      height: 52,
      child: FilledButton(
        style: FilledButton.styleFrom(backgroundColor: color, textStyle: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: 0.8, fontSize: 15)),
        onPressed: busy ? null : onPressed,
        child: busy ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5)) : Text(text),
      ),
    );

Color _demandColor(double d) => d >= 1.05 ? AppColors.success : (d >= 0.9 ? AppColors.warning : AppColors.danger);

/// Wybór auta z poziomem paliwa ⛽. `null` = bez auta (autobus / auto-dobór).
class _CarPicker extends StatelessWidget {
  const _CarPicker({required this.data, required this.value, required this.onChanged, required this.noneLabel, this.showTaxi = false});
  final CrewData data;
  final String? value;
  final ValueChanged<String?> onChanged;
  final String? noneLabel;
  final bool showTaxi;
  @override
  Widget build(BuildContext context) {
    final inUse = data.carsInUse;
    final items = <Widget>[
      if (noneLabel != null) _carTile(context, null, noneLabel!, null, false),
      for (final g in data.garage) _carTile(context, g.id, carName(g.id), g, inUse.contains(g.id)),
    ];
    if (data.garage.isEmpty) {
      items.add(const Padding(
        padding: EdgeInsets.symmetric(vertical: 6),
        child: Text('Garaż jest pusty — kup auto w Salonie.', style: TextStyle(color: AppColors.textSecondary)),
      ));
    }
    return Column(children: items);
  }

  Widget _carTile(BuildContext context, String? id, String name, GarageCar? g, bool busy) {
    final selected = value == id;
    final spec = g?.spec;
    final fuel = g?.fuel ?? 0;
    final lowFuel = g != null && spec != null && fuel < spec.fuel * 2;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Material(
        color: selected ? AppColors.primary.withValues(alpha: 0.14) : AppColors.surfaceLight,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12), side: BorderSide(color: selected ? AppColors.primary : AppColors.border)),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: busy ? null : () => onChanged(id),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(children: [
              Text(g == null ? '🚌' : '🚗', style: const TextStyle(fontSize: 20)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(name, style: TextStyle(fontWeight: FontWeight.w700, color: busy ? AppColors.textSecondary : AppColors.textPrimary)),
                  if (g != null)
                    Text(
                      busy
                          ? 'W trasie — zajęte'
                          : showTaxi && spec != null
                              ? 'Taxi: ≈ ${spec.taxiNetPerHour.toStringAsFixed(1)} \$/h netto · ${spec.seats} miejsc'
                              : '${spec?.seats ?? 1} miejsc · ${spec?.fuel.toStringAsFixed(0) ?? '?'}% paliwa/hop',
                      style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                ]),
              ),
              if (g != null) ...[
                Text('⛽ ${fuel.round()}%',
                    style: TextStyle(fontWeight: FontWeight.w800, color: lowFuel ? AppColors.danger : (fuel < 50 ? AppColors.warning : AppColors.success))),
              ],
              const SizedBox(width: 8),
              Icon(selected ? Icons.radio_button_checked_rounded : Icons.radio_button_off_rounded,
                  color: selected ? AppColors.primary : AppColors.textSecondary, size: 20),
            ]),
          ),
        ),
      ),
    );
  }
}

class _HoursPicker extends StatelessWidget {
  const _HoursPicker({required this.options, required this.value, required this.onChanged, this.bonus = false});
  final List<int> options;
  final int value;
  final ValueChanged<int> onChanged;
  final bool bonus;
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      for (final h in options)
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 3),
            child: ChoiceChip(
              showCheckmark: false,
              selected: value == h,
              onSelected: (_) => onChanged(h),
              selectedColor: AppColors.primary.withValues(alpha: 0.25),
              side: BorderSide(color: value == h ? AppColors.primary : AppColors.border),
              label: SizedBox(
                width: double.infinity,
                child: Column(children: [
                  Text('$h h', style: const TextStyle(fontWeight: FontWeight.w800)),
                  if (bonus)
                    Text('+${shiftBonus[h] ?? 0}%', style: TextStyle(fontSize: 11, color: (shiftBonus[h] ?? 0) > 0 ? AppColors.success : AppColors.textSecondary)),
                ]),
              ),
            ),
          ),
        ),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Modal SERVICE: wysyłka na zmianę → POST /npcs/{id}/dispatch
// ---------------------------------------------------------------------------
class DispatchSheet extends ConsumerStatefulWidget {
  const DispatchSheet({super.key, required this.npc, required this.data, this.initialService, this.initialHours});
  final Npc npc;
  final CrewData data;
  final String? initialService;
  final int? initialHours;
  @override
  ConsumerState<DispatchSheet> createState() => _DispatchSheetState();
}

class _DispatchSheetState extends ConsumerState<DispatchSheet> {
  late String? service = widget.initialService ?? (widget.data.unlockedServices.isEmpty ? null : widget.data.unlockedServices.first.id);
  late int hours = widget.initialHours ?? 8;
  String? car;
  bool busy = false;

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final s = d.unlockedServices.where((x) => x.id == service).firstOrNull;
    final gross = s == null ? 0 : s.rateNow * hours * (1 + (shiftBonus[hours] ?? 0) / 100);
    final canCar = d.driversFree > 0;
    final lowEnergy = widget.npc.energy < 40;
    return _ModalFrame(
      title: 'Wyślij ${widget.npc.name} na zmianę',
      leading: NpcAvatar(widget.npc, size: 40),
      children: [
        _label('Lokacja (popyt teraz)'),
        if (d.unlockedServices.isEmpty)
          const Text('Brak odblokowanych usług.', style: TextStyle(color: AppColors.textSecondary)),
        for (final x in d.unlockedServices)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Material(
              color: service == x.id ? AppColors.primary.withValues(alpha: 0.14) : AppColors.surfaceLight,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12), side: BorderSide(color: service == x.id ? AppColors.primary : AppColors.border)),
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () => setState(() => service = x.id),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(x.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                        Text('Dzielnica ${x.district} · ${money(x.rateNow)}/h',
                            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      ]),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: _demandColor(x.demand).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(8)),
                      child: Text('popyt ${(x.demand * 100).round()}%',
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _demandColor(x.demand))),
                    ),
                  ]),
                ),
              ),
            ),
          ),
        _label('Czas zmiany (bonus auto-pilota)'),
        _HoursPicker(options: const [2, 4, 8, 12], value: hours, bonus: true, onChanged: (h) => setState(() => hours = h)),
        _label('Dojazd'),
        if (!canCar)
          const Padding(
            padding: EdgeInsets.only(bottom: 6),
            child: Text('Brak wolnego kierowcy (DRIVER) — dojazd autobusem (2× wolniej, 20 \$).',
                style: TextStyle(fontSize: 12.5, color: AppColors.warning)),
          ),
        _CarPicker(
          data: d,
          value: canCar ? car : null,
          noneLabel: 'Autobus (20 \$, 2× wolniej)',
          onChanged: canCar ? (v) => setState(() => car = v) : (_) {},
        ),
        const SizedBox(height: 8),
        Text('Szacunek: ≈ ${money(gross)} brutto (popyt i emocje zmieniają wynik)',
            style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
        if (lowEnergy)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('⚡ Energia poniżej 40 — NPC musi najpierw odpocząć.', style: TextStyle(color: AppColors.danger)),
          ),
      ],
      action: _bigButton('WYŚLIJ W TRASĘ', busy: busy, onPressed: service == null || lowEnergy ? null : () async {
        setState(() => busy = true);
        final r = await ref.read(crewActionsProvider).dispatch(widget.npc.id, service!, hours, car: canCar ? car : null);
        if (!context.mounted) return;
        if (r.ok) Navigator.pop(context);
        setState(() => busy = false);
        showCrewResult(context, r);
      }),
    );
  }
}

// ---------------------------------------------------------------------------
// Modal DRIVER: zmiana Taxi → POST /npcs/{id}/taxi
// ---------------------------------------------------------------------------
class TaxiSheet extends ConsumerStatefulWidget {
  const TaxiSheet({super.key, required this.npc, required this.data});
  final Npc npc;
  final CrewData data;
  @override
  ConsumerState<TaxiSheet> createState() => _TaxiSheetState();
}

class _TaxiSheetState extends ConsumerState<TaxiSheet> {
  int hours = 4;
  String? car;
  bool busy = false;

  @override
  void initState() {
    super.initState();
    // domyślnie najbardziej dochodowe wolne auto
    final free = widget.data.garage.where((g) => !widget.data.carsInUse.contains(g.id) && g.spec != null).toList()
      ..sort((a, b) => b.spec!.taxiNetPerHour.compareTo(a.spec!.taxiNetPerHour));
    car = free.isEmpty ? null : free.first.id;
  }

  @override
  Widget build(BuildContext context) {
    final spec = carCatalog[car];
    final g = widget.data.garage.where((x) => x.id == car).firstOrNull;
    final fuelHours = spec == null || g == null ? 0 : (g.fuel / spec.fuel).floor();
    final effHours = fuelHours < hours ? fuelHours : hours;
    final lowEnergy = widget.npc.energy < 40;
    final loyal = widget.npc.loyal ? 1.05 : 1.0;
    return _ModalFrame(
      title: 'Shift Taxi: ${widget.npc.name}',
      leading: NpcAvatar(widget.npc, size: 40),
      children: [
        _label('Długość zmiany'),
        _HoursPicker(options: const [2, 4, 8], value: hours, onChanged: (h) => setState(() => hours = h)),
        _label('Auto'),
        _CarPicker(data: widget.data, value: car, noneLabel: null, showTaxi: true, onChanged: (v) => setState(() => car = v)),
        if (spec != null) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.gold.withValues(alpha: 0.10),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.gold.withValues(alpha: 0.5)),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Przewidywany zysk netto: ≈ ${(spec.taxiNetPerHour * loyal).toStringAsFixed(1)} \$/h',
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: AppColors.gold)),
              const SizedBox(height: 4),
              Text('Brutto ${spec.taxiGrossPerHour.toStringAsFixed(0)} \$/h − paliwo ${(spec.fuel * spec.fuelPrice).toStringAsFixed(1)} \$/h − serwis ${(spec.service / 100).toStringAsFixed(0)} \$/h'
                  '${widget.npc.loyal ? ' · lojalność +5%' : ''}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              const SizedBox(height: 4),
              Text('Za $hours h: ≈ ${money(spec.taxiNetPerHour * loyal * effHours)} netto',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              if (fuelHours < hours)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text('⛽ Paliwa wystarczy na ok. $fuelHours h — zmiana skończy się wcześniej. Zatankuj auto w Garażu.',
                      style: const TextStyle(fontSize: 12.5, color: AppColors.warning)),
                ),
            ]),
          ),
        ],
        if (lowEnergy)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text('⚡ Energia poniżej 40 — kierowca musi najpierw odpocząć.', style: TextStyle(color: AppColors.danger)),
          ),
      ],
      action: _bigButton('ROZPOCZNIJ SHIFT TAXI', color: AppColors.gold, busy: busy, onPressed: car == null || lowEnergy ? null : () async {
        setState(() => busy = true);
        final r = await ref.read(crewActionsProvider).taxi(widget.npc.id, hours, car: car);
        if (!context.mounted) return;
        if (r.ok) Navigator.pop(context);
        setState(() => busy = false);
        showCrewResult(context, r);
      }),
    );
  }
}

// ---------------------------------------------------------------------------
// Rekrutacja → POST /npcs/recruit
// ---------------------------------------------------------------------------
class RecruitSheet extends ConsumerStatefulWidget {
  const RecruitSheet({super.key, required this.data});
  final CrewData data;
  @override
  ConsumerState<RecruitSheet> createState() => _RecruitSheetState();
}

class _RecruitSheetState extends ConsumerState<RecruitSheet> {
  String role = 'service';
  bool busy = false;

  Widget _role(String id, String icon, String title, String desc) {
    final sel = role == id;
    return Expanded(
      child: Material(
        color: sel ? AppColors.primary.withValues(alpha: 0.14) : AppColors.surfaceLight,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14), side: BorderSide(color: sel ? AppColors.primary : AppColors.border, width: sel ? 2 : 1)),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => setState(() => role = id),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(children: [
              Text(icon, style: const TextStyle(fontSize: 30)),
              const SizedBox(height: 6),
              Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
              const SizedBox(height: 4),
              Text(desc, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            ]),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final full = d.nextCost == null || d.count >= d.slots;
    final poor = d.nextCost != null && d.cash < d.nextCost!;
    final blocked = full || poor || !d.canRecruitHere;
    return _ModalFrame(
      title: 'Zrekrutuj pracownika',
      children: [
        _label('Rola'),
        Row(children: [
          _role('service', '🛠️', 'SERVICE', 'Pracuje w usługach, zarabia na zmianach'),
          const SizedBox(width: 10),
          _role('driver', '🚗', 'DRIVER', 'Rozwozi ekipę autami i jeździ na Taxi'),
        ]),
        const SizedBox(height: 14),
        Row(children: [
          const Text('Miejsca w Rezydencji', style: TextStyle(color: AppColors.textSecondary)),
          const Spacer(),
          Text('${d.count}/${d.slots}', style: const TextStyle(fontWeight: FontWeight.w900)),
          Text('  (max ${d.maxSlots})', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ]),
        const SizedBox(height: 6),
        MeterBar(value: d.slots == 0 ? 0 : d.count / d.slots, color: AppColors.primary),
        const SizedBox(height: 12),
        Row(children: [
          const Text('Cena kolejnego NPC', style: TextStyle(color: AppColors.textSecondary)),
          const Spacer(),
          Text(d.nextCost == null ? '—' : money(d.nextCost!),
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: poor ? AppColors.danger : AppColors.success)),
        ]),
        const SizedBox(height: 10),
        if (full)
          const Text('Brak wolnych miejsc — rozbuduj Rezydencję, aby zatrudnić więcej NPC.', style: TextStyle(color: AppColors.warning)),
        if (!full && poor) const Text('Za mało gotówki.', style: TextStyle(color: AppColors.danger)),
        if (!d.canRecruitHere)
          const Text('Rekrutacja tylko w Dzielnicy Nadmorskiej (1) i nie w podróży.', style: TextStyle(color: AppColors.warning)),
      ],
      action: _bigButton(role == 'driver' ? 'ZATRUDNIJ KIEROWCĘ' : 'ZATRUDNIJ PRACOWNIKA', busy: busy, onPressed: blocked ? null : () async {
        setState(() => busy = true);
        final r = await ref.read(crewActionsProvider).recruit(role);
        if (!context.mounted) return;
        if (r.ok) Navigator.pop(context);
        setState(() => busy = false);
        showCrewResult(context, r);
      }),
    );
  }
}

// ---------------------------------------------------------------------------
// „Zawieź do miasta”: zbiorcza wysyłka wolnych SERVICE → POST /npcs/batch {action: dispatch}
// ---------------------------------------------------------------------------
class TransportAllSheet extends ConsumerStatefulWidget {
  const TransportAllSheet({super.key, required this.data});
  final CrewData data;
  @override
  ConsumerState<TransportAllSheet> createState() => _TransportAllSheetState();
}

class _TransportAllSheetState extends ConsumerState<TransportAllSheet> {
  String service = 'best';
  int hours = 8;
  bool cars = true;
  bool busy = false;

  @override
  Widget build(BuildContext context) {
    final d = widget.data;
    final ready = d.npcs.where((n) => !n.isDriver && n.canWork).toList();
    return _ModalFrame(
      title: 'Zawieź ekipę do miasta',
      children: [
        Text('Gotowi do pracy (SERVICE, energia ≥ 40): ${ready.length}',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        if (ready.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(ready.map((n) => n.name).join(', '), style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
          ),
        _label('Cel'),
        DropdownButtonFormField<String>(
          initialValue: service,
          isExpanded: true,
          dropdownColor: AppColors.surfaceLight,
          items: [
            const DropdownMenuItem(value: 'best', child: Text('⭐ Najlepsza usługa dla każdego (asystent)')),
            for (final s in d.unlockedServices)
              DropdownMenuItem(value: s.id, child: Text('${s.name} · popyt ${(s.demand * 100).round()}%')),
          ],
          onChanged: (v) => setState(() => service = v ?? 'best'),
        ),
        _label('Czas zmiany'),
        _HoursPicker(options: const [2, 4, 8, 12], value: hours, bonus: true, onChanged: (h) => setState(() => hours = h)),
        const SizedBox(height: 8),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          value: cars && d.driversFree > 0,
          onChanged: d.driversFree > 0 ? (v) => setState(() => cars = v) : null,
          title: const Text('Rozwiozą kierowcy (auta z garażu)'),
          subtitle: Text(d.driversFree > 0
              ? 'Wolni kierowcy: ${d.driversFree}. Reszta pojedzie autobusem.'
              : 'Brak wolnego kierowcy — wszyscy pojadą autobusem (20 \$ / os.).'),
        ),
      ],
      action: _bigButton('ZAWIEŹ ${ready.length} DO PRACY', busy: busy, onPressed: ready.isEmpty ? null : () async {
        setState(() => busy = true);
        final r = await ref.read(crewActionsProvider).batch({
          'action': 'dispatch',
          'npcs': ready.map((n) => n.id).toList(),
          'service_id': service,
          'hours': hours,
          'cars': cars && d.driversFree > 0 ? 'auto' : 'none',
        });
        if (!context.mounted) return;
        if (r.ok) Navigator.pop(context);
        setState(() => busy = false);
        showCrewResult(context, r);
      }),
    );
  }
}
