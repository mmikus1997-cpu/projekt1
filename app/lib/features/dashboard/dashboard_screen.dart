import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/i18n.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../../shared/models/models.dart';
import '../auth/auth_form.dart';
import 'dashboard_providers.dart';

/// Pulpit po zalogowaniu: 3 kolumny (desktop), 2 (tablet), 1 (mobile).
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final async = ref.watch(dashboardProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(dashboardProvider), child: Text(t.t('dash.retry'))),
          ]),
        ),
      ),
      data: (d) => RefreshIndicator(
        onRefresh: () async {
          return ref.refresh(dashboardProvider.future);
        },
        child: LayoutBuilder(builder: (context, c) {
          final cols = c.maxWidth >= 1000 ? 3 : (c.maxWidth >= 600 ? 2 : 1);
          final colA = _CityColumn(d);
          final colB = _ActivityColumn(d);
          final colC = _AllianceColumn(d);
          final header = _Header(d);
          Widget body;
          if (cols == 3) {
            body = Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(child: colA), const SizedBox(width: 16),
              Expanded(child: colB), const SizedBox(width: 16),
              Expanded(child: colC),
            ]);
          } else if (cols == 2) {
            body = Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(child: Column(children: [colA, const SizedBox(height: 16), colC])),
              const SizedBox(width: 16),
              Expanded(child: colB),
            ]);
          } else {
            body = Column(children: [colA, const SizedBox(height: 16), colB, const SizedBox(height: 16), colC]);
          }
          return ListView(
            padding: EdgeInsets.all(cols == 1 ? 14 : 24),
            children: [header, const SizedBox(height: 18), body],
          );
        }),
      ),
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header(this.d);
  final DashboardData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final ev = d.timedEvent;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(d.nickname, style: Theme.of(context).textTheme.headlineLarge, key: const Key('dash-nickname')),
      const SizedBox(height: 4),
      Text('${d.worldName} · ${t.t('hud.level')} ${d.level} · Elo ${d.rating.round()}${d.classType.isEmpty ? '' : ' · ${t.t('class.${d.classType}')}'}',
          style: const TextStyle(color: AppColors.textSecondary)),
      if (ev != null) ...[
        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [AppColors.primary.withValues(alpha: 0.22), AppColors.primary.withValues(alpha: 0.05)]),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.primary.withValues(alpha: 0.35)),
          ),
          child: Row(children: [
            Text('${ev['icon'] ?? '⚡'}', style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 10),
            Expanded(
              child: Text.rich(TextSpan(children: [
                TextSpan(text: '${ev['name']}  ', style: const TextStyle(fontWeight: FontWeight.w800)),
                TextSpan(text: '${ev['desc'] ?? ''}', style: const TextStyle(color: AppColors.textSecondary)),
              ])),
            ),
          ]),
        ),
      ],
    ]);
  }
}

class _CityColumn extends ConsumerWidget {
  const _CityColumn(this.d);
  final DashboardData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final tiles = [
      ('/district', Icons.apartment_rounded, 'nav.district', AppColors.primary),
      ('/map', Icons.map_rounded, 'nav.map', const Color(0xFF34D399)),
      ('/crew', Icons.groups_rounded, 'nav.crew', const Color(0xFFA78BFA)),
      ('/club', Icons.sports_mma_rounded, 'nav.club', AppColors.danger),
    ];
    return SectionCard(
      title: t.t('dash.yourCity'),
      icon: Icons.location_city_rounded,
      child: Column(children: [
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.35,
          children: [
            for (final (path, icon, key, color) in tiles)
              _QuickTile(icon: icon, label: t.t(key), color: color, onTap: () => context.go(path)),
          ],
        ),
        if (d.nextMilestone != null) ...[
          const SizedBox(height: 14),
          MeterBar(
            value: d.activeDays / d.nextMilestone!,
            color: AppColors.gold,
            label: t.t(d.activeDays == 1 ? 'dash.staz1' : 'dash.staz', {'days': d.activeDays, 'next': d.nextMilestone}),
          ),
        ],
      ]),
    );
  }
}

class _QuickTile extends StatefulWidget {
  const _QuickTile({required this.icon, required this.label, required this.color, required this.onTap});
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  @override
  State<_QuickTile> createState() => _QuickTileState();
}

class _QuickTileState extends State<_QuickTile> {
  bool _hover = false;
  @override
  Widget build(BuildContext context) {
    // hover bez przesuwania (zasada z 0.52.2): zmienia się tylko kolor obramowania i tło
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: Material(
        color: _hover ? AppColors.surfaceLight : AppColors.background,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: widget.onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _hover ? widget.color.withValues(alpha: 0.7) : AppColors.border),
            ),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(widget.icon, color: widget.color, size: 30),
              const SizedBox(height: 8),
              Text(widget.label, style: const TextStyle(fontWeight: FontWeight.w700)),
            ]),
          ),
        ),
      ),
    );
  }
}

class _ActivityColumn extends ConsumerWidget {
  const _ActivityColumn(this.d);
  final DashboardData d;

  static const _buildingNames = {'cafe': 'Kawiarnia', 'nightclub': 'Klub Nocny'};

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final vaults = <(String, num)>[
      for (final e in d.buildingVaults.entries) (_buildingNames[e.key] ?? e.key, e.value),
    ];
    return Column(children: [
      SectionCard(
        title: t.t('dash.vaults'),
        icon: Icons.savings_rounded,
        trailing: Text(money(d.vaultTotal), style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.w800)),
        child: Column(children: [
          for (final (name, v) in vaults)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Icon(Icons.storefront_rounded,
                    size: 18, color: AppColors.textSecondary),
                const SizedBox(width: 10),
                Expanded(child: Text(name)),
                Text(money(v), style: TextStyle(fontWeight: FontWeight.w700, color: v >= 1 ? AppColors.success : AppColors.textSecondary)),
              ]),
            ),
        ]),
      ),
      const SizedBox(height: 16),
      SectionCard(
        title: '${t.t('dash.npcs')} (${d.npcCount})',
        icon: Icons.groups_rounded,
        child: d.npcs.isEmpty
            ? Text(t.t('dash.noNpcs'), style: const TextStyle(color: AppColors.textSecondary))
            : Column(children: [for (final n in d.npcs.take(5)) _NpcRow(n)]),
      ),
      if (d.alerts.isNotEmpty) ...[
        const SizedBox(height: 16),
        SectionCard(
          title: t.t('dash.alerts'),
          icon: Icons.tips_and_updates_rounded,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            for (final a in d.alerts.take(3))
              Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Text(a, style: const TextStyle(height: 1.35))),
          ]),
        ),
      ],
    ]);
  }
}

class _NpcRow extends StatelessWidget {
  const _NpcRow(this.n);
  final NpcSummary n;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(n.name, style: const TextStyle(fontWeight: FontWeight.w700))),
          Text(n.status, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
        ]),
        const SizedBox(height: 6),
        Row(children: [
          Expanded(child: MeterBar(value: n.energy / 100, color: AppColors.warning, label: '⚡ ${n.energy.round()}')),
          const SizedBox(width: 8),
          Expanded(child: MeterBar(value: n.mood / 100, color: AppColors.primary, label: '🙂 ${n.mood.round()}')),
          const SizedBox(width: 8),
          Expanded(child: MeterBar(value: n.satiety / 100, color: AppColors.success, label: '🍽 ${n.satiety.round()}')),
        ]),
      ]),
    );
  }
}

class _AllianceColumn extends ConsumerWidget {
  const _AllianceColumn(this.d);
  final DashboardData d;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final perLevel = 100;
    final inLevel = d.bpLevel >= d.bpLevels ? 1.0 : (d.bpXp % perLevel) / perLevel;
    return Column(children: [
      SectionCard(
        title: 'Battle Pass',
        icon: Icons.workspace_premium_rounded,
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: (d.bpPremium ? AppColors.gold : AppColors.textSecondary).withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(d.bpPremium ? t.t('dash.premium') : t.t('dash.free'),
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: d.bpPremium ? AppColors.gold : AppColors.textSecondary)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(t.t('dash.bpSeason', {'season': d.bpSeason, 'theme': d.bpTheme}), style: const TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 10),
          Row(children: [
            Text(t.t('dash.bpLevel', {'lvl': d.bpLevel, 'max': d.bpLevels}),
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
            const Spacer(),
            Text('${d.bpXp % perLevel} / $perLevel XP', style: const TextStyle(color: AppColors.textSecondary)),
          ]),
          const SizedBox(height: 8),
          MeterBar(value: inLevel, color: AppColors.gold, height: 8),
          const SizedBox(height: 14),
          OutlinedButton(onPressed: () => context.go('/shop'), child: const Text('Battle Pass')),
        ]),
      ),
      const SizedBox(height: 16),
      SectionCard(
        title: t.t('nav.alliance'),
        icon: Icons.shield_rounded,
        child: _AllianceInfo(d.alliance),
      ),
    ]);
  }
}

class _AllianceInfo extends ConsumerWidget {
  const _AllianceInfo(this.a);
  final AllianceSummary? a;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    if (a == null) {
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(t.t('dash.noAlliance'), style: const TextStyle(color: AppColors.textSecondary)),
        const SizedBox(height: 12),
        FilledButton.tonal(onPressed: () => context.go('/alliance'), child: Text(t.t('dash.findAlliance'))),
      ]);
    }
    final x = a!;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(color: AppColors.primary.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(8)),
          child: Text(x.tag, style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900)),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(x.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16), overflow: TextOverflow.ellipsis)),
      ]),
      const SizedBox(height: 10),
      Text('${t.t('alliance.role.${x.role}')} · ${t.t('alliance.members', {'n': x.members})} · ${t.t('alliance.fund')} ${money(x.fund)}',
          style: const TextStyle(color: AppColors.textSecondary)),
      if (x.federationName != null) ...[
        const SizedBox(height: 6),
        Text('🤝 ${t.t('alliance.federation')}: ${x.federationName} (${x.federationOrgs})', style: const TextStyle(color: AppColors.gold)),
      ],
      const SizedBox(height: 12),
      FilledButton.tonal(onPressed: () => context.go('/alliance'), child: Text(t.t('alliance.open'))),
    ]);
  }
}
