import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../i18n/i18n.dart';
import '../theme/app_theme.dart';

/// Pełnoekranowe tło: granatowy gradient z poświatą electric blue i delikatną siatką miasta.
class CityBackground extends StatelessWidget {
  const CityBackground({super.key, required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: RadialGradient(
          center: Alignment(0, -0.9),
          radius: 1.4,
          colors: [Color(0xFF16305A), AppColors.background],
          stops: [0, 0.75],
        ),
      ),
      child: CustomPaint(painter: _SkylinePainter(), child: child),
    );
  }
}

class _SkylinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = AppColors.primary.withValues(alpha: 0.05)
      ..strokeWidth = 1;
    for (double x = 0; x < size.width; x += 48) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (double y = 0; y < size.height; y += 48) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    // sylwetka miasta przy dolnej krawędzi
    final city = Paint()..color = const Color(0xFF0F1A30);
    final w = size.width, h = size.height;
    const heights = [0.10, 0.18, 0.13, 0.25, 0.16, 0.30, 0.12, 0.21, 0.15, 0.27, 0.11, 0.19, 0.14, 0.23];
    final bw = w / heights.length;
    for (var i = 0; i < heights.length; i++) {
      final bh = h * heights[i] * 0.8;
      canvas.drawRect(Rect.fromLTWH(i * bw + 2, h - bh, bw - 4, bh), city);
    }
    final win = Paint()..color = AppColors.primary.withValues(alpha: 0.18);
    for (var i = 0; i < heights.length; i++) {
      final bh = h * heights[i] * 0.8;
      for (double y = h - bh + 10; y < h - 8; y += 16) {
        if (((i * 7 + y) ~/ 16) % 3 == 0) canvas.drawRect(Rect.fromLTWH(i * bw + bw / 2 - 3, y, 6, 6), win);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Logo tekstowe CITY EMPIRE.
class Logo extends StatelessWidget {
  const Logo({super.key, this.size = 40});
  final double size;
  @override
  Widget build(BuildContext context) {
    return Column(mainAxisSize: MainAxisSize.min, children: [
      Container(
        width: size * 1.6,
        height: size * 1.6,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(size * 0.4),
          gradient: const LinearGradient(colors: [AppColors.primary, Color(0xFF2563EB)]),
          boxShadow: [BoxShadow(color: AppColors.primary.withValues(alpha: 0.45), blurRadius: 32)],
        ),
        child: Icon(Icons.location_city_rounded, size: size, color: Colors.white),
      ),
      SizedBox(height: size * 0.4),
      Text.rich(
        TextSpan(children: [
          const TextSpan(text: 'CITY '),
          TextSpan(text: 'EMPIRE', style: TextStyle(color: AppColors.primary, shadows: [
            Shadow(color: AppColors.primary.withValues(alpha: 0.6), blurRadius: 18),
          ])),
        ]),
        style: TextStyle(fontSize: size * 0.9, fontWeight: FontWeight.w900, letterSpacing: size * 0.06),
      ),
    ]);
  }
}

final _money = NumberFormat.decimalPattern('pl');
String money(num v) => '${_money.format(v.round())} \$';

/// Karta sekcji z nagłówkiem.
class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.title, required this.child, this.icon, this.trailing});
  final String title;
  final IconData? icon;
  final Widget child;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            if (icon != null) ...[Icon(icon, size: 18, color: AppColors.primary), const SizedBox(width: 8)],
            Expanded(
              child: Text(title.toUpperCase(),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, letterSpacing: 1.2, color: AppColors.textSecondary)),
            ),
            ?trailing,
          ]),
          const SizedBox(height: 12),
          child,
        ]),
      ),
    );
  }
}

/// Cienki pasek postępu z etykietą.
class MeterBar extends StatelessWidget {
  const MeterBar({super.key, required this.value, required this.color, this.label, this.height = 6});
  final double value; // 0–1
  final Color color;
  final String? label;
  final double height;
  @override
  Widget build(BuildContext context) {
    final bar = ClipRRect(
      borderRadius: BorderRadius.circular(height),
      child: LinearProgressIndicator(
        value: value.clamp(0, 1),
        minHeight: height,
        color: color,
        backgroundColor: AppColors.surfaceLight,
      ),
    );
    if (label == null) return bar;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label!, style: Theme.of(context).textTheme.bodySmall),
      const SizedBox(height: 4),
      bar,
    ]);
  }
}

/// Ekran-zaślepka dla tras, które powstaną w kolejnych krokach.
class PlaceholderScreen extends ConsumerWidget {
  const PlaceholderScreen({super.key, required this.titleKey, required this.icon});
  final String titleKey;
  final IconData icon;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 56, color: AppColors.primary.withValues(alpha: 0.7)),
          const SizedBox(height: 16),
          Text(t.t(titleKey), style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(t.t('common.soon'), style: const TextStyle(color: AppColors.textSecondary), textAlign: TextAlign.center),
        ]),
      ),
    );
  }
}

/// Przełącznik języka (pl/en/de/fr).
class LanguageMenu extends ConsumerWidget {
  const LanguageMenu({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return PopupMenuButton<String>(
      tooltip: t.t('common.language'),
      initialValue: t.lang,
      onSelected: (l) => ref.read(translationsProvider.notifier).setLanguage(l),
      itemBuilder: (_) => [for (final l in supportedLanguages) PopupMenuItem(value: l, child: Text(l.toUpperCase()))],
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.language, size: 18, color: AppColors.textSecondary),
          const SizedBox(width: 6),
          Text(t.lang.toUpperCase(), style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.textSecondary)),
        ]),
      ),
    );
  }
}
