import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../../shared/models/models.dart';
import '../crew/crew_providers.dart';
import '../dashboard/dashboard_providers.dart';
import '../district/district_providers.dart';

/// Okno pokazane raz na sesję (per świat) po wejściu do gry.
final welcomeShownProvider = StateProvider<int?>((_) => null);

/// „Co się wydarzyło” — podsumowanie offline z /dashboard (Etap 1, rozbudowa Etap 4).
/// „ODBIERZ WSZYSTKO” = kaskada istniejących akcji: skarbce (Kawiarnia + Klub Nocny) i wypłaty ekipy.
Future<void> showWelcomeBack(BuildContext context, DashboardData d) => showDialog(
      context: context,
      builder: (_) => WelcomeBackDialog(d: d),
    );

class WelcomeBackDialog extends ConsumerStatefulWidget {
  const WelcomeBackDialog({super.key, required this.d});
  final DashboardData d;
  @override
  ConsumerState<WelcomeBackDialog> createState() => _WelcomeBackDialogState();
}

enum _Step { idle, busy, done }

class _WelcomeBackDialogState extends ConsumerState<WelcomeBackDialog> {
  _Step _step = _Step.idle;
  final _collected = <String, num>{}; // klucz pozycji → odebrana kwota (kaskada ✓)
  num _total = 0;
  String? _error;

  String _away(int m) {
    if (m < 60) return '$m min';
    if (m < 60 * 24) return '${m ~/ 60} h ${m % 60} min';
    return '${m ~/ (60 * 24)} d ${(m ~/ 60) % 24} h';
  }

  Future<void> _collectAll() async {
    setState(() => _step = _Step.busy);
    final d = widget.d;
    // 1) skarbce
    if (d.vaultTotal >= 1) {
      final r = await ref.read(districtActionsProvider).collectAll();
      if (!mounted) return;
      final got = r.ok ? d.vaultTotal.floor() : 0; // komunikatów skarbca nie parsujemy (zaczynają się od ikony)
      if (!r.ok) _error = r.message;
      setState(() {
        _collected['vault'] = got;
        _total += got;
      });
      await Future.delayed(const Duration(milliseconds: 450));
    }
    // 2) wypłaty ekipy (rozliczenie zmian)
    if (d.crewEarned >= 1 && mounted) {
      final r = await ref.read(crewActionsProvider).collect();
      if (!mounted) return;
      final m = RegExp(r'\+(\d+)').firstMatch(r.message);
      final got = num.tryParse(m?.group(1) ?? '') ?? 0;
      setState(() {
        _collected['crew'] = got;
        _total += got;
      });
    }
    ref.invalidate(dashboardProvider);
    if (mounted) setState(() => _step = _Step.done);
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final away = d.awayMinutes;
    final money$ = <(String, String, String, num)>[
      if (d.vaultTotal >= 1) ('vault', '💰', 'Skarbce zarobiły', d.vaultTotal),
      if (d.crewEarned >= 1) ('crew', '👷', 'Pracownicy zarobili', d.crewEarned),
    ];
    final info = <(String, String, Color?)>[
      for (final c in d.brokenCars) ('🔧', "Auto '${d.carName(c)}' wymaga naprawy (zużycie 100%)", AppColors.warning),
      if (d.burntNpcs.isNotEmpty) ('😡', 'Wypaleni NPC: ${d.burntNpcs.join(', ')} — daj im odpocząć', AppColors.danger),
      for (final e in d.recentEvents.take(3)) ('📰', e, null),
      for (final a in d.alerts.take(2)) ('💡', a, null),
    ];
    return AlertDialog(
      key: const Key('welcome-back'),
      backgroundColor: AppColors.surface,
      title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Text('Co się wydarzyło', style: TextStyle(fontWeight: FontWeight.w900)),
        const SizedBox(height: 4),
        Text(away == null ? 'Witaj z powrotem, ${d.nickname}!' : 'Nie było Cię ${_away(away)}, ${d.nickname}.',
            style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
      ]),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            for (final (key, icon, label, amount) in money$) _MoneyRow(icon: icon, label: label, amount: amount, collected: _collected[key]),
            if (money$.isNotEmpty && info.isNotEmpty) const Divider(height: 22),
            for (final (icon, text, color) in info)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(icon, style: const TextStyle(fontSize: 17)),
                  const SizedBox(width: 10),
                  Expanded(child: Text(text, style: TextStyle(color: color, fontWeight: color == null ? null : FontWeight.w700))),
                ]),
              ),
            if (_step != _Step.idle) ...[
              const SizedBox(height: 14),
              Center(
                child: TweenAnimationBuilder<num>(
                  key: const Key('welcome-total'),
                  tween: Tween(begin: 0, end: _total),
                  duration: const Duration(milliseconds: 900),
                  curve: Curves.easeOutCubic,
                  builder: (_, v, _) => Text('+ ${money(v.round())}',
                      style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w900, color: AppColors.gold)),
                ),
              ),
            ],
            if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: const TextStyle(color: AppColors.danger))),
          ]),
        ),
      ),
      actionsAlignment: MainAxisAlignment.spaceBetween,
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(_step == _Step.done ? 'Gotowe' : 'Zamknij')),
        if (money$.isNotEmpty && _step != _Step.done)
          FilledButton.icon(
            key: const Key('welcome-collect'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.gold,
              foregroundColor: Colors.black,
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
              textStyle: const TextStyle(fontWeight: FontWeight.w900, letterSpacing: .6),
            ),
            onPressed: _step == _Step.busy ? null : _collectAll,
            icon: _step == _Step.busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                : const Icon(Icons.download_rounded),
            label: const Text('ODBIERZ WSZYSTKO'),
          ),
      ],
    );
  }
}

/// Pozycja kwoty: po odbiorze wjeżdża „✓ +kwota” (kaskada animacji).
class _MoneyRow extends StatelessWidget {
  const _MoneyRow({required this.icon, required this.label, required this.amount, this.collected});
  final String icon, label;
  final num amount;
  final num? collected;
  @override
  Widget build(BuildContext context) {
    final done = collected != null;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 350),
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: (done ? AppColors.success : AppColors.gold).withValues(alpha: .10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: (done ? AppColors.success : AppColors.gold).withValues(alpha: .5)),
      ),
      child: Row(children: [
        Text(icon, style: const TextStyle(fontSize: 20)),
        const SizedBox(width: 10),
        Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 350),
          transitionBuilder: (c, a) => SlideTransition(position: Tween(begin: const Offset(0, .6), end: Offset.zero).animate(a), child: FadeTransition(opacity: a, child: c)),
          child: Text(
            done ? '✓ +${money(collected!)}' : money(amount),
            key: ValueKey(done),
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: done ? AppColors.success : AppColors.gold),
          ),
        ),
      ]),
    );
  }
}
