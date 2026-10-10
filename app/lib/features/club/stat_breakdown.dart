import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import 'club_models.dart';

/// Rozbicie jednej statystyki (z backendu: GET /gear → statBreakdown).
/// total = base (trening) + gear (zestawy ekwipunku) + unique (unikaty z Lochu) + other (np. Pływanie).
class StatPart {
  StatPart(Map<String, dynamic> m)
      : stat = (m['stat'] as num?)?.toInt() ?? 0,
        base = (m['base'] as num?)?.toDouble() ?? 0,
        gear = (m['gear'] as num?)?.toDouble() ?? 0,
        unique = (m['unique'] as num?)?.toDouble() ?? 0,
        other = (m['other'] as num?)?.toDouble() ?? 0,
        total = (m['total'] as num?)?.toDouble() ?? 0;
  final int stat;
  final double base, gear, unique, other, total;

  static String _n(double v) => v == v.roundToDouble() ? '${v.round()}' : v.toStringAsFixed(1);
  static String _p(double v) => '${v >= 0 ? '+' : '−'}${_n(v.abs())}';

  String get totalText => _n(total);
  bool get boosted => total > base + 0.05;

  /// Treść dymka: skąd dokładnie bierze się wartość.
  String get detail => [
        '${statIcons[stat]} ${statNames[stat]}: ${_n(total)}',
        '• Trening (baza): ${_n(base)}',
        if (gear != 0) '• Ekwipunek (zestawy): ${_p(gear)}',
        if (unique != 0) '• Unikaty z Lochu: ${_p(unique)}',
        if (other.abs() >= 0.05) '• Pływanie / inne: ${_p(other)}',
      ].join('\n');
}

List<StatPart> parseBreakdown(Object? raw) => [for (final m in (raw as List?) ?? const []) if (m is Map) StatPart(m.cast<String, dynamic>())];

/// Wartość statystyki z dymkiem (desktop: najechanie, telefon: dotknięcie).
class StatValue extends StatelessWidget {
  const StatValue({super.key, required this.p, this.style, this.child});
  final StatPart p;
  final TextStyle? style;
  final Widget? child;
  @override
  Widget build(BuildContext context) => Tooltip(
        message: p.detail,
        triggerMode: TooltipTriggerMode.tap,
        waitDuration: const Duration(milliseconds: 150),
        showDuration: const Duration(seconds: 4),
        textStyle: const TextStyle(fontSize: 12, color: Colors.white, height: 1.45),
        decoration: BoxDecoration(color: const Color(0xF20B1220), borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.border)),
        padding: const EdgeInsets.all(10),
        child: MouseRegion(cursor: SystemMouseCursors.help, child: child ?? Text(p.totalText, style: style)),
      );
}

/// Pasek „Twoje statystyki”: łączne wartości 5 statystyk, rozbicie w dymku.
class StatSummary extends StatelessWidget {
  const StatSummary({super.key, required this.parts, this.footer});
  final List<StatPart> parts;
  final Widget? footer;
  @override
  Widget build(BuildContext context) => Container(
        key: const Key('stat-summary'),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(14), border: Border.all(color: AppColors.border)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Row(children: [
            Text('Twoje statystyki', style: TextStyle(fontWeight: FontWeight.w800)),
            SizedBox(width: 6),
            Text('· najedź lub dotknij, by zobaczyć skąd', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
          ]),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final p in parts)
              StatValue(
                key: Key('stat-total-${p.stat}'),
                p: p,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceLight,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: p.boosted ? AppColors.success.withValues(alpha: .5) : AppColors.border),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(statIcons[p.stat], style: const TextStyle(fontSize: 15)),
                    const SizedBox(width: 5),
                    Text('${statNames[p.stat]} ', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                    Text(p.totalText, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: p.boosted ? AppColors.success : AppColors.textPrimary)),
                  ]),
                ),
              ),
          ]),
          if (footer != null) ...[const SizedBox(height: 6), footer!],
        ]),
      );
}
