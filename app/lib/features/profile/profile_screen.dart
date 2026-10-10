import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/perf/perf_mode.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart' show ErrorBanner;
import 'profile_providers.dart';

/// Profil / Konto: podsumowanie gracza (awatar z ramką, Prestiż, staż) + Battle Pass (1–30, Premium 400💎, odbiór nagród).
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prof = ref.watch(profileProvider);
    final bp = ref.watch(battlePassProvider);
    final pad = MediaQuery.sizeOf(context).width >= 600 ? 24.0 : 12.0;
    Widget err(Object e, VoidCallback retry) => Column(children: [ErrorBanner('$e'), FilledButton(onPressed: retry, child: const Text('Spróbuj ponownie'))]);
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(profileProvider);
        await ref.read(battlePassProvider.future);
      },
      child: ListView(padding: EdgeInsets.fromLTRB(pad, pad, pad, pad + 70), children: [
        const Text('Profil', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        const _PerfCard(), // E5: Tryb Eco na górze — łatwo znaleźć na słabszym telefonie
        const SizedBox(height: 12),
        prof.when(
          skipLoadingOnRefresh: true,
          loading: () => const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
          error: (e, _) => err(e, () => ref.invalidate(profileProvider)),
          data: (p) => _Summary(p: p),
        ),
        const SizedBox(height: 16),
        bp.when(
          skipLoadingOnRefresh: true,
          loading: () => const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator())),
          error: (e, _) => err(e, () => ref.invalidate(battlePassProvider)),
          data: (b) => _BattlePassCard(bp: b),
        ),
      ]),
    );
  }
}

/// Kolor ramki z identyfikatora (sezon Elo: diamond/gold/silver; Battle Pass: bp-*).
Color frameColor(String id) {
  if (id.contains('diamond') || id.contains('legend')) return const Color(0xFF7DD3FC);
  if (id.contains('gold')) return AppColors.gold;
  if (id.contains('silver')) return const Color(0xFFCBD5E1);
  if (id.startsWith('bp-')) return const Color(0xFFB57BFF);
  return AppColors.primary;
}

String frameLabel(String id) {
  final m = RegExp(r'^season-(\d+)-(\w+)$').firstMatch(id);
  if (m != null) {
    final t = switch (m.group(2)) { 'diamond' => 'Diamentowa', 'gold' => 'Złota', 'silver' => 'Srebrna', _ => m.group(2)! };
    return '$t · sezon ${m.group(1)}';
  }
  if (id.startsWith('bp-')) return id.endsWith('legend') ? 'Legendy (Battle Pass)' : 'Battle Pass ${id.split('-').skip(1).take(2).join('-')}';
  return id;
}

class _Summary extends StatelessWidget {
  const _Summary({required this.p});
  final ProfileData p;
  @override
  Widget build(BuildContext context) {
    final best = p.frames.isEmpty ? null : (p.frames.toList()..sort((a, b) => _rank(b).compareTo(_rank(a)))).first;
    final ring = best == null ? AppColors.border : frameColor(best);
    final wide = MediaQuery.sizeOf(context).width >= 700;
    final avatar = Container(
      key: const Key('profile-avatar'),
      width: 104,
      height: 104,
      padding: const EdgeInsets.all(5),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: best == null ? null : SweepGradient(colors: [ring, ring.withValues(alpha: .35), ring]),
        border: best == null ? Border.all(color: AppColors.border, width: 3) : null,
        boxShadow: best == null ? null : [BoxShadow(color: ring.withValues(alpha: .45), blurRadius: 18)],
      ),
      child: CircleAvatar(
        backgroundColor: AppColors.surfaceLight,
        child: Text(p.nickname.isEmpty ? '?' : p.nickname[0].toUpperCase(), style: const TextStyle(fontSize: 40, fontWeight: FontWeight.w900)),
      ),
    );
    final stats = Wrap(spacing: 10, runSpacing: 10, children: [
      _Stat('🏆', 'Punkty Prestiżu', '${p.prestigePoints}', key: const Key('stat-prestige')),
      _Stat('📅', 'Staż', '${p.seniorityDays} dni', key: const Key('stat-days')),
      _Stat('🔥', 'Aktywne dni', '${p.activeDays}'),
      _Stat('🔄', 'Resety', '${p.resets}'),
      _Stat('⚔️', 'Elo', '${p.rating}'),
      _Stat('📊', 'Bilans', '${p.wins}-${p.draws}-${p.losses}'),
    ]);
    final head = Column(crossAxisAlignment: wide ? CrossAxisAlignment.start : CrossAxisAlignment.center, children: [
      Text(p.nickname, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
      Text('@${p.username} · ${p.world}${p.cls != null ? ' · ${_cls(p.cls!)}' : ''}', style: const TextStyle(color: AppColors.textSecondary, fontSize: 12)),
      const SizedBox(height: 8),
      SizedBox(
        width: 260,
        child: MeterBar(
          value: p.xpNext > p.xpBase ? (p.xp - p.xpBase) / (p.xpNext - p.xpBase) : 0,
          color: AppColors.primary,
          label: 'Poziom ${p.level} · ${p.xp - p.xpBase}/${p.xpNext - p.xpBase} XP',
        ),
      ),
    ]);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (wide)
            Row(children: [avatar, const SizedBox(width: 20), Expanded(child: head)])
          else
            Column(children: [avatar, const SizedBox(height: 10), head]),
          const SizedBox(height: 16),
          stats,
          const SizedBox(height: 16),
          const Text('RAMKI (KOSMETYKA)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          const SizedBox(height: 6),
          if (p.frames.isEmpty)
            const Text('Brak ramek — zdobywa się je w sezonach Elo (Top 1000) i w Battle Passie Premium.', style: TextStyle(fontSize: 12, color: AppColors.textSecondary))
          else
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final f in p.frames)
                Chip(
                  avatar: CircleAvatar(backgroundColor: frameColor(f), radius: 7),
                  label: Text(frameLabel(f) + (f == best ? '  ★' : '')),
                  side: BorderSide(color: frameColor(f)),
                ),
            ]),
          if (p.titles.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text('TYTUŁY', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 6, children: [for (final t in p.titles.take(8)) Chip(label: Text('🎖️ $t'))]),
          ],
        ]),
      ),
    );
  }

  static int _rank(String id) => id.contains('legend') ? 5 : id.contains('diamond') ? 4 : id.contains('gold') ? 3 : id.startsWith('bp-') ? 2 : 1;
  static String _cls(String c) => switch (c) { 'bokser' => '🥊 Bokser', 'obronca' => '🛡️ Obrońca', 'szybki' => '⚡ Szybki', _ => c };
}

class _Stat extends StatelessWidget {
  const _Stat(this.icon, this.label, this.value, {super.key});
  final String icon, label, value;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.border)),
      child: Row(children: [
        Text(icon, style: const TextStyle(fontSize: 20)),
        const SizedBox(width: 8),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(value, style: const TextStyle(fontWeight: FontWeight.w900)),
            Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textSecondary), overflow: TextOverflow.ellipsis),
          ]),
        ),
      ]),
    );
  }
}

class _BattlePassCard extends ConsumerWidget {
  const _BattlePassCard({required this.bp});
  final BattlePass bp;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final daysLeft = ((bp.endsAt - DateTime.now().millisecondsSinceEpoch) / 86400000).ceil().clamp(0, 99);
    final src = bp.xpSources;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            const Text('🎫', style: TextStyle(fontSize: 30)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Battle Pass — „${bp.theme}”', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
                Text('Sezon ${bp.season} · koniec za $daysLeft dni', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
              ]),
            ),
            if (bp.premium)
              const Chip(label: Text('👑 PREMIUM'), side: BorderSide(color: AppColors.gold))
            else
              FilledButton.icon(
                key: const Key('bp-premium'),
                style: FilledButton.styleFrom(backgroundColor: AppColors.gold, foregroundColor: Colors.black),
                onPressed: bp.diamonds < bp.priceDiamonds ? null : () => _buyPremium(context, ref),
                icon: const Text('👑'),
                label: Text('Premium · ${bp.priceDiamonds}💎'),
              ),
          ]),
          const SizedBox(height: 14),
          Row(children: [
            Text('Poziom ${bp.level}/${bp.levels}', key: const Key('bp-level'), style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.primary)),
            const Spacer(),
            Text(bp.level >= bp.levels ? 'MAX' : '${bp.xpInLevel}/${bp.xpPerLevel} XP do poz. ${bp.level + 1}', style: const TextStyle(fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          MeterBar(value: bp.level >= bp.levels ? 1 : bp.xpInLevel / bp.xpPerLevel, color: AppColors.primary, height: 10),
          const SizedBox(height: 6),
          Text('XP leci w tle za akcje: NPC +${src['npc'] ?? 10} · PvP +${src['pvp'] ?? 15} · Loch +${src['dungeon'] ?? 20} · rozbudowa +${src['build'] ?? 30}'
              '${bp.premium ? '' : ' · masz ${bp.diamonds}💎'}',
              style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          if (bp.claimable > 0)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('🎁 Nagrody do odebrania: ${bp.claimable}', style: const TextStyle(color: AppColors.success, fontWeight: FontWeight.w800)),
            ),
          const SizedBox(height: 12),
          SizedBox(
            height: 196,
            child: ListView.separated(
              key: const Key('bp-track'),
              scrollDirection: Axis.horizontal,
              itemCount: bp.tracks.length,
              separatorBuilder: (_, _) => const SizedBox(width: 8),
              itemBuilder: (_, i) => _LevelColumn(bp: bp, t: bp.tracks[i]),
            ),
          ),
          const SizedBox(height: 4),
          const Row(children: [
            Text('■ ', style: TextStyle(color: AppColors.primary)),
            Text('Darmowa ścieżka   ', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            Text('■ ', style: TextStyle(color: AppColors.gold)),
            Text('Premium', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          ]),
        ]),
      ),
    );
  }

  Future<void> _buyPremium(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('👑 Battle Pass Premium'),
        content: Text('Odblokuj ścieżkę Premium na sezon „${bp.theme}” za ${bp.priceDiamonds}💎?\n'
            'Dostajesz unikatowe ramki, outfit, skórkę auta, psa i konia — także za już osiągnięte poziomy.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Anuluj')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text('Kup za ${bp.priceDiamonds}💎')),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    final r = await ref.read(battlePassActionsProvider).buyPremium();
    if (context.mounted) _snack(context, r);
  }
}

void _snack(BuildContext context, BpResult r) => ScaffoldMessenger.of(context)
    .showSnackBar(SnackBar(content: Text(r.message), backgroundColor: r.ok ? AppColors.success : AppColors.danger));

class _LevelColumn extends ConsumerWidget {
  const _LevelColumn({required this.bp, required this.t});
  final BattlePass bp;
  final BpLevel t;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reached = t.level <= bp.level;
    return SizedBox(
      width: 104,
      child: Column(children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(shape: BoxShape.circle, color: reached ? AppColors.primary : AppColors.surfaceLight, border: Border.all(color: AppColors.border)),
          child: Text('${t.level}', style: TextStyle(fontWeight: FontWeight.w900, color: reached ? Colors.black : AppColors.textSecondary)),
        ),
        const SizedBox(height: 6),
        _RewardTile(r: t.free, track: 'free', level: t.level, reached: reached, locked: false, color: AppColors.primary),
        const SizedBox(height: 6),
        _RewardTile(r: t.premium, track: 'premium', level: t.level, reached: reached, locked: !bp.premium, color: AppColors.gold),
      ]),
    );
  }
}

class _RewardTile extends ConsumerWidget {
  const _RewardTile({required this.r, required this.track, required this.level, required this.reached, required this.locked, required this.color});
  final BpReward r;
  final String track;
  final int level;
  final bool reached, locked;
  final Color color;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final canClaim = reached && !locked && !r.claimed;
    return InkWell(
      key: Key('bp-claim-$track-$level'),
      borderRadius: BorderRadius.circular(10),
      onTap: canClaim
          ? () async {
              final res = await ref.read(battlePassActionsProvider).claim(level, track);
              if (context.mounted) _snack(context, res);
            }
          : null,
      child: Container(
        height: 70,
        width: double.infinity,
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: canClaim ? color.withValues(alpha: .18) : AppColors.surfaceLight.withValues(alpha: reached ? 1 : .5),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: canClaim ? color : (r.unique ? color.withValues(alpha: .6) : AppColors.border), width: canClaim ? 2 : 1),
        ),
        child: Stack(children: [
          Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(r.icon, style: TextStyle(fontSize: 20, color: Colors.white.withValues(alpha: locked ? .4 : 1))),
              Text(r.label, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 10, color: locked ? AppColors.textSecondary : AppColors.textPrimary)),
            ]),
          ),
          if (r.claimed) const Positioned(right: 0, top: 0, child: Icon(Icons.check_circle_rounded, size: 16, color: AppColors.success)),
          if (locked) const Positioned(right: 0, top: 0, child: Icon(Icons.lock_rounded, size: 14, color: AppColors.textSecondary)),
          if (canClaim)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Text('ODBIERZ', textAlign: TextAlign.center, style: TextStyle(fontSize: 9, fontWeight: FontWeight.w900, color: color)),
            ),
        ]),
      ),
    );
  }
}


/// E5: przełącznik „Zoptymalizuj wydajność (Tryb Eco)” — dla słabszych telefonów.
class _PerfCard extends ConsumerWidget {
  const _PerfCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eco = ref.watch(ecoModeProvider);
    final saver = ref.watch(batterySaverProvider).valueOrNull ?? false;
    return Card(
      child: Column(children: [
        SwitchListTile(
          key: const Key('eco-toggle'),
          secondary: const Icon(Icons.eco_outlined, color: AppColors.success),
          title: const Text('Zoptymalizuj wydajność (Tryb Eco)', style: TextStyle(fontWeight: FontWeight.w700)),
          subtitle: const Text('Wyłącza płynny dzień/noc, animacje aut NPC (zostaje linia trasy), dym, łódkę, sarnę i cienie.'),
          value: eco,
          onChanged: (v) => ref.read(ecoModeProvider.notifier).set(v),
        ),
        if (saver)
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Text('🔋 Telefon jest w trybie oszczędzania baterii — animacje mapy są wstrzymane.', style: TextStyle(fontSize: 12, color: AppColors.warning)),
          ),
      ]),
    );
  }
}
