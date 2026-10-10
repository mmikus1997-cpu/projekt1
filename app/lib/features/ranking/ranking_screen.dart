import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../auth/auth_form.dart' show ErrorBanner;
import 'ranking_providers.dart';

/// Ranking Świata: ⚔️ PvP (Elo, sezon miesięczny) · 🐉 Lochy · 🏆 Prestiż · 💰 Bogacze.
class RankingScreen extends ConsumerWidget {
  const RankingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(rankingProvider);
    final pad = MediaQuery.sizeOf(context).width >= 600 ? 24.0 : 12.0;
    final wide = MediaQuery.sizeOf(context).width >= 600;
    return DefaultTabController(
      length: 4,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: EdgeInsets.fromLTRB(pad, pad, pad, 0),
          child: Row(children: [
            const Expanded(child: Text('Ranking Świata', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800))),
            IconButton(tooltip: 'Odśwież', onPressed: () => ref.invalidate(rankingProvider), icon: const Icon(Icons.refresh_rounded)),
          ]),
        ),
        TabBar(
          isScrollable: !wide,
          tabAlignment: wide ? TabAlignment.fill : TabAlignment.start,
          tabs: const [
            Tab(key: Key('rk-tab-pvp'), text: '⚔️ Top PvP'),
            Tab(key: Key('rk-tab-dungeon'), text: '🐉 Top Lochy'),
            Tab(key: Key('rk-tab-prestige'), text: '🏆 Top Prestiż'),
            Tab(key: Key('rk-tab-wealth'), text: '💰 Top Bogaczy'),
          ],
        ),
        Expanded(
          child: async.when(
            skipLoadingOnRefresh: true,
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  ErrorBanner('$e'),
                  FilledButton(onPressed: () => ref.invalidate(rankingProvider), child: const Text('Spróbuj ponownie')),
                ]),
              ),
            ),
            data: (d) => TabBarView(children: [
              _Board(
                board: d.pvp,
                header: _Banner(
                  icon: '⚔️',
                  title: 'Ranking miesięczny Elo — sezon ${d.season}',
                  subtitle: d.daysLeft <= 1 ? 'Koniec sezonu dziś! Top 10: ramka diamentowa + 600💎' : 'Koniec sezonu za ${d.daysLeft} dni · Top 10: ramka diamentowa + 600💎 · Top 100: złota + 200💎',
                  color: AppColors.primary,
                ),
                value: (r) => '${r.value} Elo',
                sub: (r) => 'W ${r.raw['wins']} · R ${r.raw['draws']} · P ${r.raw['losses']}',
              ),
              _Board(
                board: d.dungeon,
                header: const _Banner(icon: '🐉', title: 'Rekordziści Lochu', subtitle: 'Kolejność: najpierw Nightmare, potem Hard, potem Normal — najwyższe piętro w trybie.', color: AppColors.danger),
                value: (r) => r.value == 0 ? '—' : 'piętro ${r.value}',
                sub: (r) => 'Normal ${r.raw['normal']} · Hard ${r.raw['hard']} · Nightmare ${r.raw['nightmare']}',
                badge: (r) => switch ('${r.raw['mode']}') {
                  'nightmare' => ('NIGHTMARE', AppColors.danger),
                  'hard' => ('HARD', AppColors.warning),
                  _ => ('NORMAL', AppColors.textSecondary),
                },
              ),
              _Board(
                board: d.prestige,
                header: const _Banner(icon: '🏆', title: 'Sala Chwały', subtitle: 'Gracze z największą liczbą resetów (Prestiż) na tym świecie.', color: AppColors.gold),
                value: (r) => '${r.value}× reset',
                sub: (r) => 'Poziom ${r.level}',
              ),
              _Board(
                board: d.wealth,
                header: const _Banner(icon: '💰', title: 'Najbogatsi', subtitle: 'Gotówka postaci na tym świecie.', color: AppColors.success),
                value: (r) => money(r.value),
                sub: (r) => 'Poziom ${r.level}',
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.icon, required this.title, required this.subtitle, required this.color});
  final String icon, title, subtitle;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: .5)),
      ),
      child: Row(children: [
        Text(icon, style: const TextStyle(fontSize: 28)),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
            Text(subtitle, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ]),
        ),
      ]),
    );
  }
}

class _Board extends ConsumerWidget {
  const _Board({required this.board, required this.header, required this.value, required this.sub, this.badge});
  final RankBoard board;
  final Widget header;
  final String Function(RankRow) value, sub;
  final (String, Color) Function(RankRow)? badge;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pad = MediaQuery.sizeOf(context).width >= 600 ? 24.0 : 12.0;
    final me = board.me;
    final meVisible = me != null && board.rows.any((r) => r.id == me.id);
    return RefreshIndicator(
      onRefresh: () => ref.refresh(rankingProvider.future),
      child: ListView(padding: EdgeInsets.fromLTRB(pad, 16, pad, pad + 70), children: [
        header,
        const SizedBox(height: 12),
        if (board.rows.isEmpty)
          const Padding(padding: EdgeInsets.all(24), child: Text('Brak graczy w rankingu.', textAlign: TextAlign.center)),
        Card(
          child: Column(children: [
            for (final r in board.rows) _row(context, r, me?.id == r.id),
          ]),
        ),
        if (me != null && !meVisible) ...[
          const SizedBox(height: 8),
          const Text('TWOJA POZYCJA', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
          Card(child: _row(context, me, true)),
        ],
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('Graczy w rankingu: ${board.total}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
        ),
      ]),
    );
  }

  Widget _row(BuildContext context, RankRow r, bool mine) {
    final medal = switch (r.place) { 1 => '🥇', 2 => '🥈', 3 => '🥉', _ => null };
    final b = badge?.call(r);
    return Container(
      color: mine ? AppColors.primary.withValues(alpha: .12) : null,
      child: ListTile(
        key: Key('rank-${r.place}'),
        dense: MediaQuery.sizeOf(context).width < 600,
        leading: SizedBox(
          width: 40,
          child: Center(
            child: medal != null
                ? Text(medal, style: const TextStyle(fontSize: 24))
                : Text('#${r.place}', style: const TextStyle(fontWeight: FontWeight.w800, color: AppColors.textSecondary)),
          ),
        ),
        title: Row(children: [
          if (r.tag != null) ...[
            Text('[${r.tag}] ', style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w800)),
          ],
          Flexible(child: Text(r.nickname + (mine ? '  (Ty)' : ''), overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700))),
          if (b != null) ...[
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
              decoration: BoxDecoration(border: Border.all(color: b.$2), borderRadius: BorderRadius.circular(4)),
              child: Text(b.$1, style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: b.$2)),
            ),
          ],
        ]),
        subtitle: Text(sub(r), style: const TextStyle(fontSize: 11)),
        trailing: Text(value(r), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
    );
  }
}
