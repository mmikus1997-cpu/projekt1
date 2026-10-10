import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/dashboard/dashboard_providers.dart';
import '../../features/district/district_providers.dart';
import '../i18n/i18n.dart';
import '../theme/app_theme.dart';
import '../theme/breakpoints.dart';
import 'common.dart';
import 'inbox_dialog.dart';

/// Górny HUD: gotówka, energia (pasek), diamenty, poziom, powiadomienia.
class HudBar extends ConsumerWidget {
  const HudBar({super.key, this.leading, this.onAvatar});
  final Widget? leading;
  /// Etap 1 UI v2: klik w awatar → okno „Profil / Battle Pass”.
  final VoidCallback? onAvatar;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final dash = ref.watch(dashboardProvider).valueOrNull;
    final compact = Breakpoints.isMobile(context);
    final energy = dash?.energy ?? 0;
    // liczniki z prawdziwych zdarzeń: 🔔 = systemowe, ✉️ = PvP/sojusz + czat (odświeżane, gdy backend zgłosi nowe)
    ref.listen(dashboardProvider.select((a) => a.valueOrNull?.unread), (p, n) {
      if (p != null && p != n) ref.invalidate(inboxProvider);
    });
    final inbox = ref.watch(inboxProvider).valueOrNull;
    final bellN = inbox?.unreadOf(false) ?? (dash?.eventsUnread ?? 0);
    final mailN = (dash?.dmUnread ?? 0) + (inbox?.unreadOf(true) ?? 0);
    final chips = <Widget>[
      // Etap 4: kasa „dolicza się” animacją przy każdej zmianie (np. po ODBIERZ WSZYSTKO)
      TweenAnimationBuilder<num>(
        key: const Key('hud-cash'),
        tween: Tween(end: dash?.cash ?? 0),
        duration: const Duration(milliseconds: 1100),
        curve: Curves.easeOutCubic,
        builder: (_, v, _) => _Chip(icon: Icons.payments_rounded, color: AppColors.success, label: t.t('hud.cash'),
            value: dash == null ? '—' : money(v.round()), compact: compact),
      ),
      _EnergyChip(energy: energy, max: dash?.energyMax ?? 240, label: t.t('hud.energy'), compact: compact),
      _Chip(icon: Icons.diamond_rounded, color: const Color(0xFF7DD3FC), label: t.t('hud.diamonds'),
          value: dash == null ? '—' : '${dash.diamonds}', compact: compact),
      _Chip(icon: Icons.military_tech_rounded, color: AppColors.gold, label: t.t('hud.level'),
            value: dash == null ? '—' : '${dash.level}', compact: compact),
      if (dash != null && dash.vaultTotal >= 1) _VaultChip(total: dash.vaultTotal, compact: compact),
    ];
    return Material(
      color: AppColors.surface,
      child: Container(
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: AppColors.border))),
        padding: EdgeInsets.symmetric(horizontal: compact ? 10 : 20, vertical: compact ? 8 : 10),
        child: SafeArea(
          bottom: false,
          child: Row(children: [
            if (leading != null) ...[leading!, const SizedBox(width: 12)],
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(children: [
                  for (final c in chips) Padding(padding: EdgeInsets.only(right: compact ? 6 : 10), child: c),
                ]),
              ),
            ),
            // Ranking zawsze pod ręką (też na telefonie) — skrót do Społeczność → Ranking
            IconButton(
              key: const Key('hud-ranking'),
              visualDensity: compact ? VisualDensity.compact : null,
              onPressed: () => GoRouter.of(context).go('/community?tab=ranking'),
              icon: const Icon(Icons.emoji_events_outlined, color: AppColors.gold),
              tooltip: 'Ranking',
            ),
            Badge(
              isLabelVisible: mailN > 0,
              label: Text('$mailN'),
              child: IconButton(
                key: const Key('hud-mail'),
                visualDensity: compact ? VisualDensity.compact : null,
                onPressed: () => showInbox(context, InboxKind.messages),
                icon: const Icon(Icons.mail_outline_rounded),
                tooltip: 'Wiadomości',
              ),
            ),
            Badge(
              isLabelVisible: bellN > 0,
              label: Text('$bellN'),
              child: IconButton(
                key: const Key('hud-bell'),
                onPressed: () => showInbox(context, InboxKind.system),
                icon: const Icon(Icons.notifications_none_rounded),
                tooltip: 'Powiadomienia systemowe',
              ),
            ),
            if (onAvatar != null) ...[
              const SizedBox(width: 4),
              Tooltip(
                message: 'Profil · Battle Pass',
                child: InkWell(
                  key: const Key('hud-avatar'),
                  customBorder: const CircleBorder(),
                  onTap: onAvatar,
                  child: CircleAvatar(
                    radius: compact ? 16 : 18,
                    backgroundColor: AppColors.primary.withValues(alpha: 0.22),
                    child: Text(
                      (dash?.nickname.isNotEmpty ?? false) ? dash!.nickname.substring(0, 1).toUpperCase() : '?',
                      style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w900),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({super.key, required this.icon, required this.color, required this.label, required this.value, required this.compact});
  final IconData icon;
  final Color color;
  final String label, value;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceLight,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: 6),
        Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          if (!compact) Text(label, style: const TextStyle(fontSize: 10, color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
        ]),
      ]),
    );
  }
}

class _EnergyChip extends StatelessWidget {
  const _EnergyChip({required this.energy, required this.max, required this.label, required this.compact});
  final double energy;
  final double max;
  final String label;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: compact ? 104 : 150,
      padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 12, vertical: 6),
      decoration: BoxDecoration(color: AppColors.surfaceLight, borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        const Icon(Icons.bolt_rounded, size: 18, color: AppColors.warning),
        const SizedBox(width: 6),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(compact ? '${energy.floor()}/${max.round()}' : '$label ${energy.floor()}/${max.round()}',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            MeterBar(value: energy / max, color: AppColors.warning, height: 5),
          ]),
        ),
      ]),
    );
  }
}

/// Zielony skarbiec w HUD: klik = odbiór Kawiarni + Klubu Nocnego (zastępuje prawy panel szybkich akcji).
class _VaultChip extends ConsumerStatefulWidget {
  const _VaultChip({required this.total, required this.compact});
  final num total;
  final bool compact;
  @override
  ConsumerState<_VaultChip> createState() => _VaultChipState();
}

class _VaultChipState extends ConsumerState<_VaultChip> {
  bool _busy = false;
  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.success.withValues(alpha: 0.14),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        key: const Key('vault-collect'),
        borderRadius: BorderRadius.circular(12),
        onTap: _busy ? null : _collect,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: widget.compact ? 8 : 12, vertical: 8),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            _busy
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.success))
                : const Icon(Icons.savings_rounded, size: 18, color: AppColors.success),
            const SizedBox(width: 6),
            Text(widget.compact ? money(widget.total) : 'Odbierz ${money(widget.total)}',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppColors.success)),
          ]),
        ),
      ),
    );
  }

  Future<void> _collect() async {
    setState(() => _busy = true);
    final messenger = ScaffoldMessenger.of(context);
    final r = await ref.read(districtActionsProvider).collectAll();
    if (!mounted) return;
    setState(() => _busy = false);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        behavior: SnackBarBehavior.floating,
        content: Text(r.ok ? '💰 ${r.message}' : r.message),
        backgroundColor: r.ok ? AppColors.success : AppColors.danger,
      ));
  }
}
