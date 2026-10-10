import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart' show ErrorBanner;
import 'alliance_providers.dart';

/// Hub Sojuszu: bez sojuszu → załóż / dołącz; w sojuszu → Członkowie · Skarbiec · Budynki · Terytoria.
class AllianceScreen extends ConsumerWidget {
  const AllianceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(allianceProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(allianceProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
      ),
      data: (d) => d.inAlliance ? _AllianceHub(d: d) : _NoAlliance(d: d),
    );
  }
}

void _toast(BuildContext context, AllyResult r) => ScaffoldMessenger.of(context)
    .showSnackBar(SnackBar(content: Text(r.message), backgroundColor: r.ok ? AppColors.success : AppColors.danger));

double _pad(BuildContext c) => MediaQuery.sizeOf(c).width >= 600 ? 24 : 12;

// ───────────────────────────────────────────── bez sojuszu
class _NoAlliance extends ConsumerWidget {
  const _NoAlliance({required this.d});
  final AllianceData d;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pad = _pad(context);
    return RefreshIndicator(
      onRefresh: () => ref.refresh(allianceProvider.future),
      child: ListView(padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 70), children: [
        const Text('Sojusz', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Nie należysz jeszcze do sojuszu. Załóż własny albo dołącz do istniejącego — wspólny Skarbiec, budynki i walka o terytoria.',
            style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        const SizedBox(height: 16),
        if (d.invitations.isNotEmpty) ...[
          SectionCard(
            title: 'Zaproszenia',
            icon: Icons.mail_rounded,
            child: Column(children: [
              for (final inv in d.invitations)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.shield_rounded, color: AppColors.gold),
                  title: Text('[${inv['tag']}] ${inv['name']}'),
                  trailing: Wrap(spacing: 6, children: [
                    OutlinedButton(
                        onPressed: () async => _toast(context, await ref.read(allianceActionsProvider).invite((inv['id'] as num).toInt(), false)),
                        child: const Text('Odrzuć')),
                    FilledButton(
                        key: Key('invite-accept-${inv['id']}'),
                        onPressed: () async => _toast(context, await ref.read(allianceActionsProvider).invite((inv['id'] as num).toInt(), true)),
                        child: const Text('Dołącz')),
                  ]),
                ),
            ]),
          ),
          const SizedBox(height: 12),
        ],
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(children: [
              const Text('🛡️', style: TextStyle(fontSize: 36)),
              const SizedBox(width: 14),
              const Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Stwórz Sojusz', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                  Text('Zostaniesz Liderem. Nazwa 3–32 znaki, tag 2–5 liter/cyfr.', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                ]),
              ),
              FilledButton.icon(
                key: const Key('ally-create'),
                onPressed: () => showDialog<void>(context: context, builder: (_) => const _CreateDialog()),
                icon: const Icon(Icons.add_rounded),
                label: const Text('Załóż'),
              ),
            ]),
          ),
        ),
        const SizedBox(height: 12),
        _JoinList(d: d),
      ]),
    );
  }
}

class _JoinList extends ConsumerStatefulWidget {
  const _JoinList({required this.d});
  final AllianceData d;
  @override
  ConsumerState<_JoinList> createState() => _JoinListState();
}

class _JoinListState extends ConsumerState<_JoinList> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final q = _q.trim().toLowerCase();
    final list = widget.d.organizations
        .where((o) => q.isEmpty || '${o['name']}'.toLowerCase().contains(q) || '${o['tag']}'.toLowerCase().contains(q))
        .toList()
      ..sort((a, b) => ((b['prestige'] as num?) ?? 0).compareTo((a['prestige'] as num?) ?? 0));
    return SectionCard(
      title: 'Dołącz do sojuszu (${widget.d.organizations.length})',
      icon: Icons.search_rounded,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        TextField(
          decoration: const InputDecoration(prefixIcon: Icon(Icons.search_rounded), hintText: 'Szukaj po nazwie lub tagu', isDense: true),
          onChanged: (v) => setState(() => _q = v),
        ),
        const SizedBox(height: 8),
        if (list.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('Brak sojuszy — bądź pierwszy i załóż własny!', textAlign: TextAlign.center, style: TextStyle(color: AppColors.textSecondary)),
          ),
        for (final o in list)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: CircleAvatar(backgroundColor: AppColors.surfaceLight, child: Text('${o['tag']}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800))),
            title: Text('${o['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
            subtitle: Text('👥 ${o['members']}/20 · 🏆 prestiż ${o['prestige']} · lider ${o['leader_name']}'
                '${(o['held'] as List?)?.isNotEmpty == true ? ' · 🗺️ ${(o['held'] as List).join(', ')}' : ''}'),
            trailing: widget.d.appliedTo == (o['id'] as num).toInt()
                ? const Chip(label: Text('Podanie wysłane'))
                : OutlinedButton(
                    key: Key('ally-apply-${o['id']}'),
                    onPressed: (o['members'] as num) >= 20 ? null : () => _apply(o),
                    child: Text((o['members'] as num) >= 20 ? 'Pełny' : 'Złóż podanie'),
                  ),
          ),
      ]),
    );
  }

  Future<void> _apply(Map<String, dynamic> o) async {
    final ctrl = TextEditingController(text: 'Cześć! Chętnie dołączę do [${o['tag']}] i pomogę w rozwoju.');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('Podanie do [${o['tag']}]'),
        content: TextField(controller: ctrl, maxLines: 3, maxLength: 200, decoration: const InputDecoration(labelText: 'Wiadomość (10–200 znaków)')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Anuluj')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Wyślij')),
        ],
      ),
    );
    if (ok == true && mounted) _toast(context, await ref.read(allianceActionsProvider).apply((o['id'] as num).toInt(), ctrl.text.trim()));
  }
}

class _CreateDialog extends ConsumerStatefulWidget {
  const _CreateDialog();
  @override
  ConsumerState<_CreateDialog> createState() => _CreateDialogState();
}

class _CreateDialogState extends ConsumerState<_CreateDialog> {
  final _name = TextEditingController(), _tag = TextEditingController(), _desc = TextEditingController();
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    final tagOk = RegExp(r'^[A-Z0-9]{2,5}$').hasMatch(_tag.text.trim().toUpperCase());
    final nameOk = _name.text.trim().length >= 3 && _name.text.trim().length <= 32;
    return AlertDialog(
      title: const Text('🛡️ Stwórz Sojusz'),
      content: SizedBox(
        width: 420,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(key: const Key('ally-name'), controller: _name, maxLength: 32, decoration: const InputDecoration(labelText: 'Nazwa sojuszu'), onChanged: (_) => setState(() {})),
          TextField(
            key: const Key('ally-tag'),
            controller: _tag,
            maxLength: 5,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(labelText: 'Tag (2–5 znaków, np. LCM)'),
            onChanged: (_) => setState(() {}),
          ),
          TextField(controller: _desc, maxLength: 180, maxLines: 2, decoration: const InputDecoration(labelText: 'Opis (opcjonalnie)')),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Anuluj')),
        FilledButton(
          key: const Key('ally-create-submit'),
          onPressed: _busy || !tagOk || !nameOk
              ? null
              : () async {
                  setState(() => _busy = true);
                  final r = await ref.read(allianceActionsProvider).create(_name.text.trim(), _tag.text.trim().toUpperCase(), _desc.text.trim());
                  if (!mounted) return;
                  setState(() => _busy = false);
                  if (r.ok) Navigator.pop(context);
                  _toast(context, r);
                },
          child: _busy ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Załóż sojusz'),
        ),
      ],
    );
  }
}

// ───────────────────────────────────────────── w sojuszu
class _AllianceHub extends ConsumerWidget {
  const _AllianceHub({required this.d});
  final AllianceData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pad = _pad(context);
    final wide = MediaQuery.sizeOf(context).width >= 600;
    return DefaultTabController(
      length: 4,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: EdgeInsets.fromLTRB(pad, pad, pad, 0),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: .15), borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.primary)),
              child: Text(d.tag, style: const TextStyle(fontWeight: FontWeight.w900, color: AppColors.primary)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(d.name, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis),
                Text('Twoja rola: ${AllyMember({'role': d.myRole}).roleLabel} · 👥 ${d.members.length}/20 · 🏆 prestiż ${d.prestige}'
                    '${d.myHeld.isNotEmpty ? ' · 🗺️ ${d.myHeld.length} terytoria' : ''}',
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              ]),
            ),
            Text(money(d.fund), style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.success)),
          ]),
        ),
        TabBar(
          isScrollable: !wide,
          tabAlignment: wide ? TabAlignment.fill : TabAlignment.start,
          tabs: const [
            Tab(icon: Icon(Icons.groups_rounded), text: 'Członkowie'),
            Tab(icon: Icon(Icons.savings_rounded), text: 'Skarbiec'),
            Tab(icon: Icon(Icons.account_balance_rounded), text: 'Budynki'),
            Tab(icon: Icon(Icons.map_rounded), text: 'Terytoria'),
          ],
        ),
        Expanded(
          child: TabBarView(children: [
            _MembersTab(d: d),
            _TreasuryTab(d: d),
            _BuildingsTab(d: d),
            _TerritoryTab(d: d),
          ]),
        ),
      ]),
    );
  }
}

Widget _tabList(BuildContext context, WidgetRef ref, List<Widget> children) {
  final pad = _pad(context);
  return RefreshIndicator(
    onRefresh: () => ref.refresh(allianceProvider.future),
    child: ListView(padding: EdgeInsets.fromLTRB(pad, 16, pad, pad + 70), children: children),
  );
}

class _MembersTab extends ConsumerWidget {
  const _MembersTab({required this.d});
  final AllianceData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final leader = d.myRole == 'leader';
    return _tabList(context, ref, [
      if (d.isOfficer && d.applications.isNotEmpty) ...[
        SectionCard(
          title: 'Podania (${d.applications.length})',
          icon: Icons.how_to_reg_rounded,
          child: Column(children: [
            for (final a in d.applications)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('${a['nickname']}'),
                subtitle: Text('${a['text']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                trailing: Wrap(spacing: 6, children: [
                  IconButton(
                      tooltip: 'Odrzuć',
                      onPressed: () async => _toast(context, await ref.read(allianceActionsProvider).application((a['id'] as num).toInt(), false)),
                      icon: const Icon(Icons.close_rounded, color: AppColors.danger)),
                  IconButton(
                      tooltip: 'Przyjmij',
                      onPressed: () async => _toast(context, await ref.read(allianceActionsProvider).application((a['id'] as num).toInt(), true)),
                      icon: const Icon(Icons.check_rounded, color: AppColors.success)),
                ]),
              ),
          ]),
        ),
        const SizedBox(height: 12),
      ],
      SectionCard(
        title: 'Członkowie ${d.members.length}/20',
        icon: Icons.groups_rounded,
        child: Column(children: [
          for (final m in d.members)
            ListTile(
              key: Key('member-${m.id}'),
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: m.role == 'leader' ? AppColors.gold.withValues(alpha: .25) : AppColors.surfaceLight,
                child: Text(m.nickname.isEmpty ? '?' : m.nickname[0].toUpperCase()),
              ),
              title: Text(m.nickname + (m.id == d.characterId ? '  (Ty)' : ''), style: const TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text(m.roleLabel, style: TextStyle(color: m.role == 'leader' ? AppColors.gold : m.role == 'officer' ? AppColors.primary : AppColors.textSecondary)),
              trailing: leader && m.role != 'leader'
                  ? TextButton(
                      onPressed: () async => _toast(context, await ref.read(allianceActionsProvider).role(m.id, m.role == 'officer' ? 'member' : 'officer')),
                      child: Text(m.role == 'officer' ? 'Zdegraduj' : 'Awansuj na Oficera'),
                    )
                  : null,
            ),
        ]),
      ),
      const SizedBox(height: 12),
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          style: TextButton.styleFrom(foregroundColor: AppColors.danger),
          onPressed: () async {
            final ok = await showDialog<bool>(
              context: context,
              builder: (c) => AlertDialog(
                title: const Text('Opuścić sojusz?'),
                content: Text(leader ? 'Jako Lider — jeśli zostaniesz sam, sojusz zostanie rozwiązany.' : 'Twoje wpłaty zostają w Skarbcu sojuszu.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Anuluj')),
                  FilledButton(style: FilledButton.styleFrom(backgroundColor: AppColors.danger), onPressed: () => Navigator.pop(c, true), child: const Text('Opuść')),
                ],
              ),
            );
            if (ok == true && context.mounted) _toast(context, await ref.read(allianceActionsProvider).leave());
          },
          icon: const Icon(Icons.logout_rounded),
          label: const Text('Opuść sojusz'),
        ),
      ),
    ]);
  }
}

class _TreasuryTab extends ConsumerStatefulWidget {
  const _TreasuryTab({required this.d});
  final AllianceData d;
  @override
  ConsumerState<_TreasuryTab> createState() => _TreasuryTabState();
}

class _TreasuryTabState extends ConsumerState<_TreasuryTab> {
  double _amount = 500;
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    return _tabList(context, ref, [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(children: [
            const Text('🏦', style: TextStyle(fontSize: 40)),
            const Text('Fundusz sojuszu', style: TextStyle(color: AppColors.textSecondary)),
            Text(money(d.fund), key: const Key('ally-fund'), style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: AppColors.success)),
            const SizedBox(height: 4),
            const Text('Z Funduszu Lider i Oficerowie ulepszają budynki i inwestują w terytoria.',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ]),
        ),
      ),
      const SizedBox(height: 12),
      SectionCard(
        title: 'Wpłać gotówkę',
        icon: Icons.add_card_rounded,
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(
              child: Slider(
                value: _amount,
                min: 100,
                max: 5000,
                divisions: 49,
                label: money(_amount),
                onChanged: (v) => setState(() => _amount = v),
              ),
            ),
            SizedBox(width: 90, child: Text(money(_amount), textAlign: TextAlign.end, style: const TextStyle(fontWeight: FontWeight.w800))),
          ]),
          Wrap(spacing: 8, children: [
            for (final v in [100, 500, 1000, 2500, 5000])
              ActionChip(label: Text(money(v)), onPressed: () => setState(() => _amount = v.toDouble())),
          ]),
          const SizedBox(height: 12),
          FilledButton.icon(
            key: const Key('ally-fund-submit'),
            onPressed: _busy
                ? null
                : () async {
                    setState(() => _busy = true);
                    final r = await ref.read(allianceActionsProvider).fund(_amount.round());
                    if (!mounted) return;
                    setState(() => _busy = false);
                    _toast(context, r);
                  },
            icon: const Icon(Icons.savings_rounded),
            label: Text('Wpłać ${money(_amount)}'),
          ),
          const SizedBox(height: 6),
          const Text('Jednorazowo 100–5 000 \$. Wpłata liczy się do Dystynkcji dnia.', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
        ]),
      ),
    ]);
  }
}

class _BuildingsTab extends ConsumerWidget {
  const _BuildingsTab({required this.d});
  final AllianceData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cols = MediaQuery.sizeOf(context).width >= 900 ? 3 : (MediaQuery.sizeOf(context).width >= 600 ? 2 : 1);
    final b = d.buildings;
    return _tabList(context, ref, [
      if (!d.isOfficer)
        const Padding(
          padding: EdgeInsets.only(bottom: 12),
          child: Text('🔒 Ulepszać budynki mogą tylko Lider i Oficerowie (z Funduszu sojuszu). Bonusy działają dla wszystkich członków.',
              style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ),
      GridView.count(
        crossAxisCount: cols,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: cols == 1 ? 2.4 : 1.35,
        children: [
          for (final x in b)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Text(x.icon, style: const TextStyle(fontSize: 28)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(x.name, style: const TextStyle(fontWeight: FontWeight.w800)),
                        Text('Poziom ${x.level}/${d.allyMax}', style: const TextStyle(fontSize: 12, color: AppColors.primary)),
                      ]),
                    ),
                  ]),
                  const SizedBox(height: 8),
                  MeterBar(value: x.level / d.allyMax, color: AppColors.primary),
                  const SizedBox(height: 8),
                  Text(x.desc, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                  Text('Teraz: −${x.pct * x.level}%', style: const TextStyle(fontSize: 12, color: AppColors.success, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  SizedBox(
                    width: double.infinity,
                    child: x.level >= d.allyMax
                        ? const OutlinedButton(onPressed: null, child: Text('Poziom maksymalny'))
                        : FilledButton(
                            key: Key('ally-build-${x.id}'),
                            onPressed: !d.isOfficer || d.fund < d.allyCost[x.level]
                                ? null
                                : () async => _toast(context, await ref.read(allianceActionsProvider).build(x.id)),
                            child: Text('Ulepsz · ${money(d.allyCost[x.level])}'),
                          ),
                  ),
                ]),
              ),
            ),
        ],
      ),
    ]);
  }
}

class _TerritoryTab extends ConsumerWidget {
  const _TerritoryTab({required this.d});
  final AllianceData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = d.territories;
    return _tabList(context, ref, [
      Text('Sojusz z ponad ${(d.controlShare * 100).round()}% udziałów w dzielnicy przejmuje kontrolę: +5% do zarobków NPC członków w tej dzielnicy. '
          '${d.isOfficer ? 'Inwestujesz z Funduszu (${money(d.fund)}).' : 'Inwestują Lider i Oficerowie z Funduszu.'}',
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      const SizedBox(height: 12),
      for (final x in t) ...[
        _TerritoryCard(x: x, d: d),
        const SizedBox(height: 10),
      ],
    ]);
  }
}

class _TerritoryCard extends ConsumerWidget {
  const _TerritoryCard({required this.x, required this.d});
  final Territory x;
  final AllianceData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mine = d.myHeld.contains(x.district);
    final ctrl = d.controlShare;
    final color = mine ? AppColors.success : (x.myShare > 0 ? AppColors.primary : AppColors.textSecondary);
    return Card(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: mine ? AppColors.success : AppColors.border)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Text(mine ? '🏴' : (x.controlled ? '🚩' : '🗺️'), style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(x.district, style: const TextStyle(fontWeight: FontWeight.w800)),
                Text(
                  mine
                      ? 'KONTROLUJECIE · bonus +5% NPC'
                      : x.controlled
                          ? 'Kontroluje [${x.holderTag}]'
                          : x.total == 0
                              ? 'Ziemia niczyja'
                              : 'Nikt nie ma >${(ctrl * 100).round()}% — lider [${x.leaderTag}] ${(x.leaderShare * 100).toStringAsFixed(0)}%',
                  style: TextStyle(fontSize: 12, color: mine ? AppColors.success : AppColors.textSecondary),
                ),
              ]),
            ),
            Text('${(x.myShare * 100).toStringAsFixed(1)}%', key: Key('share-${x.district}'), style: TextStyle(fontWeight: FontWeight.w900, color: color)),
          ]),
          const SizedBox(height: 10),
          // pasek udziału z markerem progu 55%
          LayoutBuilder(builder: (context, c) {
            return SizedBox(
              height: 14,
              child: Stack(clipBehavior: Clip.none, children: [
                Positioned.fill(child: MeterBar(value: x.myShare, color: color, height: 10)),
                Positioned(
                  left: c.maxWidth * ctrl - 1,
                  top: -2,
                  bottom: -2,
                  child: Container(width: 2, color: AppColors.gold),
                ),
              ]),
            );
          }),
          const SizedBox(height: 4),
          Row(children: [
            Text('Wy: ${money(x.myTotal)} / razem ${money(x.total)}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            const Spacer(),
            Text('próg ${(ctrl * 100).round()}%', style: const TextStyle(fontSize: 11, color: AppColors.gold)),
          ]),
          if (d.isOfficer) ...[
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.tonalIcon(
                key: Key('invest-${x.district}'),
                onPressed: d.fund < 100 ? null : () => _invest(context, ref),
                icon: const Icon(Icons.trending_up_rounded, size: 18),
                label: const Text('Inwestuj z Funduszu'),
              ),
            ),
          ],
        ]),
      ),
    );
  }

  Future<void> _invest(BuildContext context, WidgetRef ref) async {
    final maxV = d.fund.clamp(100, 5000).toDouble();
    var v = maxV >= 1000 ? 1000.0 : maxV;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: Text('Inwestycja: ${x.district}'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(money(v), style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
            if (maxV > 100)
              Slider(value: v, min: 100, max: maxV, divisions: ((maxV - 100) / 100).round().clamp(1, 49), onChanged: (n) => set(() => v = (n / 100).round() * 100.0)),
            Text('Po inwestycji: ${(((x.myTotal + v) / (x.total + v)) * 100).toStringAsFixed(1)}% udziałów',
                style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Anuluj')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Inwestuj')),
          ],
        ),
      ),
    );
    if (ok == true && context.mounted) _toast(context, await ref.read(allianceActionsProvider).invest(x.district, v.round()));
  }
}
