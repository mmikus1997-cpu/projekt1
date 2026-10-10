import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'crew_models.dart';

/// Kolor emocji wg GDD: zielony > 50, żółty 30–50, czerwony < 30.
Color emotionColor(double v) => v > 50 ? AppColors.success : (v >= 30 ? AppColors.warning : AppColors.danger);

String fmtLeft(int ms) {
  if (ms <= 0) return '0 min';
  final m = (ms / 60000).ceil();
  return m >= 60 ? '${m ~/ 60} h ${m % 60} min' : '$m min';
}

String fmtClock(int ms) {
  final d = DateTime.fromMillisecondsSinceEpoch(ms);
  return '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
}

/// Opis bieżącego zajęcia NPC (status z backendu → zdanie po polsku).
(String, IconData, Color) npcStatus(Npc n, CrewData d, int now) {
  if (n.duty == 'taxi') {
    final left = (n.taxiUntil ?? now) - now;
    return ('Jazda Taxi (${carName(n.rideCar)}) · ${fmtLeft(left)} · +${n.taxiCash} \$', Icons.local_taxi_rounded, AppColors.gold);
  }
  if (n.duty == 'ferry') {
    return ('Wiezie ekipę (${carName(n.rideCar)})', Icons.airport_shuttle_rounded, AppColors.primary);
  }
  final svc = d.serviceName(n.service);
  final how = n.transport == 'bus' ? 'autobusem' : 'autem';
  switch (n.phase) {
    case 'to_work':
      return ('Jedzie $how do: $svc', Icons.directions_car_rounded, AppColors.primary);
    case 'working':
      final left = (n.shiftEndsAt ?? now) - now;
      return ('Pracuje w: $svc (pozostało ${fmtLeft(left)})', Icons.work_rounded, AppColors.success);
    case 'to_home':
      return ('Wraca $how do Rezydencji', Icons.home_rounded, AppColors.primary);
    case 'sleeping':
      return ('Śpi w Rezydencji (przerwa w zmianie: $svc)', Icons.bedtime_rounded, AppColors.textSecondary);
  }
  if (n.energy < 40) return ('Odpoczywa w Rezydencji (za mało energii na zmianę)', Icons.hotel_rounded, AppColors.warning);
  return ('Odpoczywa w Rezydencji — gotowy do pracy', Icons.weekend_rounded, AppColors.textSecondary);
}

const _avatarColors = [
  Color(0xFF4AA8FF), Color(0xFFA78BFA), Color(0xFFF472B6), Color(0xFF34D399),
  Color(0xFFFBBF24), Color(0xFFF87171), Color(0xFF22D3EE), Color(0xFFFB923C),
];

class NpcAvatar extends StatelessWidget {
  const NpcAvatar(this.n, {super.key, this.size = 48});
  final Npc n;
  final double size;
  @override
  Widget build(BuildContext context) {
    final idx = (int.tryParse(n.avatar.replaceAll(RegExp(r'\D'), '')) ?? n.id) % _avatarColors.length;
    final c = _avatarColors[idx];
    return Stack(clipBehavior: Clip.none, children: [
      Container(
        width: size,
        height: size,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: LinearGradient(colors: [c, c.withValues(alpha: 0.55)], begin: Alignment.topLeft, end: Alignment.bottomRight),
          border: Border.all(color: n.loyal ? AppColors.gold : AppColors.border, width: n.loyal ? 2.5 : 1.5),
        ),
        child: Text(n.name.isEmpty ? '?' : n.name.characters.first.toUpperCase(),
            style: TextStyle(fontSize: size * 0.42, fontWeight: FontWeight.w900, color: Colors.white)),
      ),
      Positioned(
        right: -4,
        bottom: -4,
        child: Container(
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(color: AppColors.surface, shape: BoxShape.circle, border: Border.all(color: AppColors.border)),
          child: Text(n.isDriver ? '🚗' : '🛠️', style: TextStyle(fontSize: size * 0.26)),
        ),
      ),
    ]);
  }
}

class _Chip extends StatelessWidget {
  const _Chip(this.text, this.color, {this.filled = false, this.tooltip});
  final String text;
  final Color color;
  final bool filled;
  final String? tooltip;
  @override
  Widget build(BuildContext context) {
    final w = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: filled ? color.withValues(alpha: 0.22) : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.7)),
      ),
      child: Text(text, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: color, letterSpacing: 0.4)),
    );
    return tooltip == null ? w : Tooltip(message: tooltip!, child: w);
  }
}

class EmotionBar extends StatelessWidget {
  const EmotionBar(this.icon, this.label, this.value, {super.key});
  final String icon, label;
  final double value;
  @override
  Widget build(BuildContext context) {
    final c = emotionColor(value);
    return Tooltip(
      message: '$label: ${value.round()}/100',
      child: Row(children: [
        SizedBox(width: 22, child: Text(icon, style: const TextStyle(fontSize: 14))),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: (value / 100).clamp(0, 1),
              minHeight: 8,
              backgroundColor: AppColors.surfaceLight,
              valueColor: AlwaysStoppedAnimation(c),
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(width: 28, child: Text('${value.round()}', textAlign: TextAlign.right,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: c))),
      ]),
    );
  }
}

/// Karta pracownika w siatce Ekipy.
class NpcCard extends StatelessWidget {
  const NpcCard({super.key, required this.n, required this.data, required this.now, required this.onTap, required this.onMenu});
  final Npc n;
  final CrewData data;
  final int now;
  final VoidCallback onTap;
  final void Function(String action) onMenu;

  @override
  Widget build(BuildContext context) {
    final (status, icon, color) = npcStatus(n, data, now);
    return Card(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: n.exhausted ? AppColors.danger.withValues(alpha: 0.7) : (n.loyal ? AppColors.gold.withValues(alpha: 0.6) : AppColors.border)),
      ),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              NpcAvatar(n),
              const SizedBox(width: 12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(n.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Wrap(spacing: 6, runSpacing: 4, children: [
                    _Chip(n.isDriver ? 'DRIVER 🚗' : 'SERVICE 🛠️', n.isDriver ? AppColors.gold : AppColors.primary, filled: true),
                    if (n.exhausted) const _Chip('PRZEMĘCZONY 😡', AppColors.danger, filled: true, tooltip: 'Emocja < 30 — zarabia o 50% mniej'),
                    if (n.loyal)
                      const _Chip('LOJALNY 👑', AppColors.gold, filled: true, tooltip: '+5% zarobku, cecha bez negatywnych efektów')
                    else
                      _Chip('⭐ ${n.loyalty}/100', AppColors.textSecondary, tooltip: '+1 za dobę bez spadku emocji poniżej 50'),
                  ]),
                ]),
              ),
              PopupMenuButton<String>(
                tooltip: 'Akcje',
                icon: const Icon(Icons.more_vert_rounded, color: AppColors.textSecondary),
                onSelected: onMenu,
                itemBuilder: (_) => [
                  if (n.busy) const PopupMenuItem(value: 'recall', child: Text('⏹  Odwołaj / zakończ')),
                  const PopupMenuItem(value: 'feed', child: Text('🍱  Nakarm (Buffet)')),
                  if (!n.busy)
                    PopupMenuItem(value: 'role', child: Text(n.isDriver ? '🛠️  Zmień rolę na SERVICE' : '🚗  Zmień rolę na DRIVER')),
                ],
              ),
            ]),
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Column(children: [
                EmotionBar('⚡', 'Energia', n.energy),
                const SizedBox(height: 4),
                EmotionBar('😊', 'Nastrój', n.mood),
                const SizedBox(height: 4),
                EmotionBar('🍔', 'Sytość', n.satiety),
              ]),
            ),
            const SizedBox(height: 10),
            if (n.traitLabel != null)
              Tooltip(
                message: n.traitActive ? (n.traitDesc ?? '') : 'Cecha działa tylko u kierowcy',
                child: Text('${n.traitIcon ?? ''} ${n.traitLabel}${n.traitActive ? '' : ' (nieaktywna)'}',
                    style: TextStyle(fontSize: 12, color: n.traitActive ? AppColors.textPrimary : AppColors.textSecondary)),
              ),
            const SizedBox(height: 6),
            Row(children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Expanded(child: Text(status, style: TextStyle(fontSize: 12.5, color: color, fontWeight: FontWeight.w600))),
            ]),
            if (n.onShift && n.shiftCash != 0)
              Padding(
                padding: const EdgeInsets.only(top: 4, left: 22),
                child: Text('Zarobione w tej zmianie: ${money(n.shiftCash)}',
                    style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary)),
              ),
          ]),
        ),
      ),
    );
  }
}
