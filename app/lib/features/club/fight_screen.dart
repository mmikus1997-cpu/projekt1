import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'club_models.dart';
import 'club_providers.dart';

/// Otwiera FightScreen na pełnym ekranie.
Future<void> openFight(BuildContext context, FightSession session) =>
    Navigator.of(context, rootNavigator: true).push(MaterialPageRoute(fullscreenDialog: true, builder: (_) => FightScreen(session: session)));

/// JEDEN uniwersalny ekran walki: PvP, Loch, Boks/MMA, wyzwania.
/// Odtwarza rounds[].exchanges[] z raportu backendu z prędkością 1x/2x/4x albo pomija do wyniku.
class FightScreen extends ConsumerStatefulWidget {
  const FightScreen({super.key, required this.session});
  final FightSession session;
  @override
  ConsumerState<FightScreen> createState() => _FightScreenState();
}

class _FightScreenState extends ConsumerState<FightScreen> with TickerProviderStateMixin {
  // animacje trafienia: potrząśnięcie + skala ciosu dla każdej strony
  late final _shake = [for (var i = 0; i < 2; i++) AnimationController(vsync: this, duration: const Duration(milliseconds: 360))];
  late final _punch = [for (var i = 0; i < 2; i++) AnimationController(vsync: this, duration: const Duration(milliseconds: 260))];
  final _log = ScrollController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(fightControllerProvider(widget.session).notifier).onExchange = _animate;
    });
  }

  void _animate(Exchange e) {
    if (!mounted) return;
    _punch[e.striker].forward(from: 0);
    if (e.landed) _shake[1 - e.striker].forward(from: 0);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_log.hasClients) _log.animateTo(_log.position.maxScrollExtent, duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
    });
  }

  @override
  void dispose() {
    for (final c in [..._shake, ..._punch]) {
      c.dispose();
    }
    _log.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final st = ref.watch(fightControllerProvider(widget.session));
    final ctl = ref.read(fightControllerProvider(widget.session).notifier);
    final speed = ref.watch(fightSpeedProvider);
    final rep = widget.session.reports[st.bout];
    final shown = rep.exchanges.take(st.step).toList();
    final hp = shown.isEmpty ? rep.hpStart : shown.last.hp;
    final last = shown.isEmpty ? null : shown.last;
    final wide = MediaQuery.sizeOf(context).width >= 700;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.surface,
        automaticallyImplyLeading: false,
        title: Text(widget.session.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
        actions: [IconButton(key: const Key('fight-close'), icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.pop(context))],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Padding(
              padding: EdgeInsets.all(wide ? 20 : 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                SpeedBar(
                  speed: speed,
                  onSpeed: ctl.setSpeed,
                  onSkip: st.finished ? null : ctl.skipAll,
                ),
                const SizedBox(height: 10),
                if (widget.session.reports.length > 1)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('${rep.title ?? ''} · ${st.bout + 1}/${widget.session.reports.length}',
                        textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textSecondary, fontWeight: FontWeight.w700)),
                  ),
                // [ Ty ] VS [ Wróg ]
                Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(child: _Fighter(side: 0, rep: rep, hp: hp[0], shake: _shake[0], punch: _punch[0], winner: st.done ? rep.winner : -1)),
                  Padding(
                    padding: const EdgeInsets.only(top: 34),
                    child: Text('VS', style: TextStyle(fontSize: wide ? 30 : 22, fontWeight: FontWeight.w900, color: AppColors.gold)),
                  ),
                  Expanded(child: _Fighter(side: 1, rep: rep, hp: hp[1], shake: _shake[1], punch: _punch[1], winner: st.done ? rep.winner : -1)),
                ]),
                const SizedBox(height: 10),
                _CurrentExchange(e: last, names: rep.names, fatigue: last == null ? 0 : (rep.fatigue[last.round] ?? 0)),
                const SizedBox(height: 10),
                Expanded(
                  child: st.finished
                      ? _Results(session: widget.session, onReplay: ctl.replay)
                      : _Log(controller: _log, ex: shown, names: rep.names),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// Pasek prędkości animacji: 1x · 2x · 4x · POMIŃ (wspólny dla klubu i walki).
class SpeedBar extends StatelessWidget {
  const SpeedBar({super.key, required this.speed, required this.onSpeed, this.onSkip, this.skipLabel = 'POMIŃ'});
  final int speed;
  final void Function(int) onSpeed;
  final VoidCallback? onSkip;
  final String skipLabel;
  @override
  Widget build(BuildContext context) {
    return Row(children: [
      const Text('Animacje:', style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      const SizedBox(width: 8),
      Expanded(
        child: SegmentedButton<int>(
          showSelectedIcon: false,
          style: SegmentedButton.styleFrom(visualDensity: VisualDensity.compact),
          segments: const [
            ButtonSegment(value: 1, label: Text('1x')),
            ButtonSegment(value: 2, label: Text('2x')),
            ButtonSegment(value: 4, label: Text('4x')),
            ButtonSegment(value: 0, label: Text('Pomiń')),
          ],
          selected: {speed},
          onSelectionChanged: (v) {
            onSpeed(v.first);
            if (v.first == 0) onSkip?.call();
          },
        ),
      ),
      if (onSkip != null) ...[
        const SizedBox(width: 8),
        FilledButton(key: const Key('fight-skip'), onPressed: onSkip, child: Text(skipLabel)),
      ],
    ]);
  }
}

class _Fighter extends StatelessWidget {
  const _Fighter({required this.side, required this.rep, required this.hp, required this.shake, required this.punch, required this.winner});
  final int side;
  final FightReport rep;
  final double hp;
  final AnimationController shake, punch;
  final int? winner; // -1 = walka trwa
  @override
  Widget build(BuildContext context) {
    final max = rep.hpStart[side] <= 0 ? 100.0 : rep.hpStart[side];
    final pct = (hp / max).clamp(0.0, 1.0);
    final color = pct > .5 ? AppColors.success : (pct >= .3 ? AppColors.warning : AppColors.danger);
    final lost = winner != -1 && winner != null && winner != side;
    final won = winner != -1 && winner == side;
    final cls = side < rep.classes.length ? rep.classes[side] : '';
    final stats = side < rep.stats.length ? rep.stats[side] : const <double>[];
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 400),
      opacity: lost ? .45 : 1,
      child: Column(children: [
        AnimatedBuilder(
          animation: Listenable.merge([shake, punch]),
          builder: (_, child) => Transform.translate(
            offset: Offset(math.sin(shake.value * math.pi * 6) * 10 * (1 - shake.value), 0),
            child: Transform.scale(scale: 1 + math.sin(punch.value * math.pi) * .14, child: child),
          ),
          // hak pod Rive: tu w przyszłości RiveAnimation zamiast emoji
          child: Container(
            width: 84,
            height: 84,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: side == 0 ? AppColors.primary.withValues(alpha: .18) : AppColors.danger.withValues(alpha: .15),
              border: Border.all(color: won ? AppColors.gold : (side == 0 ? AppColors.primary : AppColors.danger), width: won ? 4 : 2),
            ),
            child: Text(side == 0 ? '🥊' : (cls == 'Obrońca' ? '🛡️' : (cls == 'Szybki' ? '⚡' : '👊')), style: const TextStyle(fontSize: 38)),
          ),
        ),
        const SizedBox(height: 6),
        Text(rep.names[side], textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15), overflow: TextOverflow.ellipsis),
        if (cls.isNotEmpty) Text(cls, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
        if (won) const Text('🏆 ZWYCIĘZCA', style: TextStyle(color: AppColors.gold, fontWeight: FontWeight.w900, fontSize: 12)),
        const SizedBox(height: 6),
        TweenAnimationBuilder<double>(
          tween: Tween(end: pct),
          duration: const Duration(milliseconds: 350),
          builder: (_, v, _) => MeterBar(value: v, color: color, height: 10),
        ),
        const SizedBox(height: 3),
        Text('HP ${hp.toStringAsFixed(1)} / ${max.toStringAsFixed(0)} · ${(pct * 100).round()}%',
            style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w700)),
        if (stats.length == 5) ...[
          const SizedBox(height: 6),
          Wrap(alignment: WrapAlignment.center, spacing: 6, runSpacing: 2, children: [
            for (var i = 0; i < 5; i++)
              Tooltip(
                message: statNames[i],
                child: Text('${statIcons[i]}${stats[i].round()}', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
              ),
          ]),
        ],
      ]),
    );
  }
}

/// Bieżąca wymiana — duży napis z efektem (AnimatedSwitcher: skala + przezroczystość).
class _CurrentExchange extends StatelessWidget {
  const _CurrentExchange({required this.e, required this.names, required this.fatigue});
  final Exchange? e;
  final List<String> names;
  final double fatigue;
  @override
  Widget build(BuildContext context) {
    final ex = e;
    return Container(
      height: 64,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
      child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 220),
        transitionBuilder: (c, a) => ScaleTransition(scale: Tween(begin: .8, end: 1.0).animate(a), child: FadeTransition(opacity: a, child: c)),
        child: ex == null
            ? const Text('🔔 Gong! Walka się zaczyna…', key: ValueKey('start'), style: TextStyle(fontWeight: FontWeight.w700))
            : Column(key: ValueKey(ex), mainAxisSize: MainAxisSize.min, children: [
                Text('Runda ${ex.round} · ${names[ex.striker]}: ${actionPl(ex.action)}',
                    style: const TextStyle(fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis),
                Text(
                  '${actionPl(ex.reaction)} → ${resultPl(ex.result)}${ex.damage > 0 ? ' · −${ex.damage.toStringAsFixed(1)} HP' : ''}${fatigue > 0 ? ' · zmęczenie ${(fatigue * 100).round()}%' : ''}',
                  style: TextStyle(fontSize: 12, color: ex.critical ? AppColors.gold : (ex.landed ? AppColors.danger : AppColors.textSecondary), fontWeight: FontWeight.w700),
                ),
              ]),
      ),
    );
  }
}

class _Log extends StatelessWidget {
  const _Log({required this.controller, required this.ex, required this.names});
  final ScrollController controller;
  final List<Exchange> ex;
  final List<String> names;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
      child: ListView.builder(
        controller: controller,
        padding: const EdgeInsets.all(10),
        itemCount: ex.length,
        itemBuilder: (_, i) {
          final e = ex[i];
          final newRound = i == 0 || ex[i - 1].round != e.round;
          return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (newRound)
              Padding(
                padding: const EdgeInsets.only(top: 6, bottom: 2),
                child: Text('— RUNDA ${e.round} —', style: const TextStyle(fontSize: 11, color: AppColors.textSecondary, fontWeight: FontWeight.w800)),
              ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(children: [
                Icon(e.striker == 0 ? Icons.arrow_forward_rounded : Icons.arrow_back_rounded,
                    size: 14, color: e.striker == 0 ? AppColors.primary : AppColors.danger),
                const SizedBox(width: 6),
                Expanded(
                  child: Text('${names[e.striker]}: ${actionPl(e.action)} · ${actionPl(e.reaction)} · ${resultPl(e.result)}',
                      style: const TextStyle(fontSize: 13)),
                ),
                Text(e.damage > 0 ? '−${e.damage.toStringAsFixed(1)}' : '0',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: e.critical ? AppColors.gold : (e.landed ? AppColors.danger : AppColors.textSecondary))),
              ]),
            ),
          ]);
        },
      ),
    );
  }
}

/// Po walce: wynik, nagrody $ / XP / drop, powtórka.
/// Koszt energii piętra wg trybu Lochu (dungeon.py MODES).
const dungeonEnergy = {'normal': 8, 'hard': 15, 'nightmare': 25};

class _Results extends ConsumerStatefulWidget {
  const _Results({required this.session, required this.onReplay});
  final FightSession session;
  final VoidCallback onReplay;
  @override
  ConsumerState<_Results> createState() => _ResultsState();
}

class _ResultsState extends ConsumerState<_Results> {
  bool _busy = false;

  /// QA 2: od razu kolejne piętro — nowa walka zastępuje bieżący ekran (bez wychodzenia do menu).
  Future<void> _nextFloor() async {
    setState(() => _busy = true);
    final nav = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final r = await ref.read(clubActionsProvider).dungeon(widget.session.dungeonMode!);
    if (!mounted) return;
    if (r.fight != null) {
      nav.pushReplacement(MaterialPageRoute(fullscreenDialog: true, builder: (_) => FightScreen(session: r.fight!)));
      return;
    }
    setState(() => _busy = false);
    messenger.showSnackBar(SnackBar(content: Text(r.message), backgroundColor: AppColors.danger, behavior: SnackBarBehavior.floating));
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    final onReplay = widget.onReplay;
    final reps = session.reports;
    final wins = reps.where((r) => r.winner == 0).length;
    final single = reps.length == 1;
    final w = reps.last.winner;
    final title = single ? (w == 0 ? '🏆 ZWYCIĘSTWO!' : (w == null ? '🤝 REMIS' : '💥 PORAŻKA')) : '🥊 Turniej: $wins/${reps.length} wygranych';
    final color = single ? (w == 0 ? AppColors.gold : (w == null ? AppColors.warning : AppColors.danger)) : AppColors.gold;
    final r = session.rewards;
    return SingleChildScrollView(
      child: Container(
        key: const Key('fight-results'),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: color.withValues(alpha: .6))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          TweenAnimationBuilder<double>(
            tween: Tween(begin: .6, end: 1),
            duration: const Duration(milliseconds: 450),
            curve: Curves.elasticOut,
            builder: (_, v, c) => Transform.scale(scale: v, child: c),
            child: Text(title, textAlign: TextAlign.center, style: TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: color)),
          ),
          if (r.message != null && r.message!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(r.message!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textSecondary)),
          ],
          const SizedBox(height: 14),
          Wrap(alignment: WrapAlignment.center, spacing: 10, runSpacing: 8, children: [
            _Pill('💵 +${money(r.cash)}', AppColors.success),
            _Pill('⭐ +${r.xp} XP', AppColors.primary),
            for (final x in r.extra) _Pill(x, AppColors.gold),
          ]),
          if (r.drops.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text('DROP', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
            for (final d in r.drops) Text(d, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
          const SizedBox(height: 16),
          if (session.dungeonMode != null && w == 0) ...[
            FilledButton(
              key: const Key('fight-next-floor'),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.gold,
                foregroundColor: const Color(0xFF1A1300),
                minimumSize: const Size.fromHeight(56),
                textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, letterSpacing: .8),
              ),
              onPressed: _busy ? null : _nextFloor,
              child: _busy
                  ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                  : Text('⏩ NASTĘPNE PIĘTRO (${dungeonEnergy[session.dungeonMode] ?? 8}⚡)'),
            ),
            const SizedBox(height: 10),
          ],
          Row(children: [
            Expanded(child: OutlinedButton.icon(onPressed: onReplay, icon: const Icon(Icons.replay_rounded), label: const Text('Powtórka'))),
            const SizedBox(width: 10),
            Expanded(child: FilledButton(key: const Key('fight-done'), onPressed: () => Navigator.pop(context), child: const Text('Wróć do klubu'))),
          ]),
        ]),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill(this.text, this.color);
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(color: color.withValues(alpha: .12), borderRadius: BorderRadius.circular(20), border: Border.all(color: color.withValues(alpha: .5))),
        child: Text(text, style: TextStyle(fontWeight: FontWeight.w800, color: color)),
      );
}
