import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../../shared/models/models.dart' show NpcRide;
import '../dashboard/dashboard_providers.dart';
import '../../core/perf/perf_mode.dart';
import 'map_ambient.dart';
import 'map_layout.dart';
import 'map_rides.dart';
import 'map_providers.dart';
import 'map_textures.dart';
import 'map_widgets.dart' show demandBadge, demandColor;

// ───────────────────────────── zaznaczenie (panel szczegółów)
enum MapSelKind { district, service, landmark }

class MapSelection {
  const MapSelection(this.kind, this.id);
  final MapSelKind kind;
  final String id;
  @override
  bool operator ==(Object o) => o is MapSelection && o.kind == kind && o.id == id;
  @override
  int get hashCode => Object.hash(kind, id);
}

final mapSelectionProvider = StateProvider.autoDispose<MapSelection?>((_) => null);

// ───────────────────────────── cykl dzień / noc
/// auto = wg czasu serwera (strefa lokalna gracza); day / night = podgląd ręczny.
final dayNightModeProvider = StateProvider<String>((_) => 'auto');

/// 0 = pełny dzień, 1 = głęboka noc. Zmierzch 18–21, świt 5–7.
double nightFactor(int serverMs, String mode) {
  if (mode == 'day') return 0;
  if (mode == 'night') return 1;
  final t = DateTime.fromMillisecondsSinceEpoch(serverMs).toLocal();
  final h = t.hour + t.minute / 60;
  if (h >= 7 && h < 18) return 0;
  if (h >= 18 && h < 21) return (h - 18) / 3;
  if (h >= 5 && h < 7) return 1 - (h - 5) / 2;
  return 1;
}

/// Nakładka koloru: granat nocą, ciepły pomarańcz w połowie zmierzchu/świtu.
Color nightOverlay(double f) {
  final dusk = math.sin(math.pi * f) * 0.16;
  final night = Color.fromRGBO(4, 8, 28, 0.52 * f);
  return Color.alphaBlend(Color.fromRGBO(255, 140, 60, dusk), night);
}

// ───────────────────────────── plansza
class MapBoard extends ConsumerStatefulWidget {
  const MapBoard({super.key, required this.d, required this.controller, required this.viewport, this.onDistrict});
  final MapData d;
  /// M3: klik dzielnicy → przejście do widoku okolicy (gdy null — sam panel, jak wcześniej)
  final void Function(int id)? onDistrict;
  final TransformationController controller;
  final Size viewport;
  @override
  ConsumerState<MapBoard> createState() => _MapBoardState();
}

class _MapBoardState extends ConsumerState<MapBoard> with SingleTickerProviderStateMixin {
  // „Mapa żyje”: delikatne pulsowanie świateł i znacznika TU JESTEŚ (tylko jeden ticker).
  late final AnimationController _pulse = AnimationController(vsync: this, duration: const Duration(seconds: 3));
  bool _fx = true;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_syncPulse);
  }

  /// E5: pulsowanie tyka tylko, gdy efekty są włączone i znacznik TU JESTEŚ jest w kadrze
  /// (wcześniej ticker kręcił się zawsze = stałe obciążenie CPU). Nocne światła zostają wtedy statyczne.
  void _syncPulse() {
    final vis = MatrixUtils.inverseTransformRect(widget.controller.value, Offset.zero & widget.viewport);
    final run = _fx && vis.contains(widget.d.layout.district(widget.d.here).pos);
    if (run && !_pulse.isAnimating) _pulse.repeat(reverse: true);
    if (!run && _pulse.isAnimating) _pulse.stop();
  }

  @override
  void didUpdateWidget(covariant MapBoard old) {
    super.didUpdateWidget(old);
    if (old.controller != widget.controller) {
      old.controller.removeListener(_syncPulse);
      widget.controller.addListener(_syncPulse);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_syncPulse);
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final l = d.layout;
    final sel = ref.watch(mapSelectionProvider);
    final fx = ref.watch(effectsOnProvider); // E5: false = Tryb Eco / oszczędzanie baterii
    final dnMode = ref.watch(dayNightModeProvider);
    // Eco: bez płynnego dnia/nocy (tylko ręczny podgląd nocy zostaje), bez pulsowania
    final night = fx || dnMode != 'auto' ? nightFactor(d.serverTime, dnMode) : 0.0;
    _fx = fx;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _syncPulse();
    });
    void select(MapSelection? s) => ref.read(mapSelectionProvider.notifier).state = s;

    // Plansza zawsze wypełnia ekran: nie da się oddalić ani przesunąć tak, by pokazać puste tło poza grafiką
    final cover = coverScale(widget.viewport, l);
    return InteractiveViewer(
      transformationController: widget.controller,
      constrained: false,
      minScale: cover,
      maxScale: 3.5,
      boundaryMargin: EdgeInsets.zero,
      child: GestureDetector(
        key: const Key('map-bg'),
        behavior: HitTestBehavior.opaque,
        onTap: () => select(null), // tap w tło zamyka panel
        child: SizedBox(
          width: l.width,
          height: l.height,
          child: Stack(clipBehavior: Clip.none, children: [
            // M1: malowana grafika regionu; fallback = teren wektorowy
            Positioned.fill(child: MapArtLayer(layout: l, fallback: RepaintBoundary(child: CustomPaint(painter: TerrainPainter(l, roads: false))))),
            // E5: tekstury PNG pod drogami → wektorowe drogi i mosty → tekstury nad drogami
            Positioned.fill(child: MapTextureLayer(layout: l, layer: 'under')),
            if (l.artVectorRoads || l.artAsset == null)
              Positioned.fill(child: RepaintBoundary(child: CustomPaint(key: const Key('map-roads'), painter: TerrainPainter(l, ground: false)))),
            Positioned.fill(child: AmbientLayer(layout: l, view: widget.controller, viewport: widget.viewport, enabled: fx)),
            Positioned.fill(child: MapTextureLayer(layout: l, layer: 'over')),
            Positioned.fill(child: CustomPaint(painter: RoutePainter(l, d.here, d.travel))),
            Positioned.fill(child: IgnorePointer(child: ColoredBox(color: nightOverlay(night)))),
            if (night > 0.05)
              Positioned.fill(
                child: IgnorePointer(
                  child: AnimatedBuilder(
                    animation: _pulse,
                    builder: (_, _) => CustomPaint(painter: GlowPainter(l, night, _pulse.value)),
                  ),
                ),
              ),
            // Etap 4: auta NPC w trasie (dane z /dashboard, odświeżane co 30 s)
            Positioned.fill(
              child: RidesLayer(
                layout: l,
                clockOffsetMs: d.clockOffsetMs,
                rides: ref.watch(dashboardProvider.select((a) => a.valueOrNull?.rides ?? const <NpcRide>[])),
                view: widget.controller,
                viewport: widget.viewport,
                animate: fx,
              ),
            ),
            for (final lm in l.landmarks)
              _LandmarkNode(lm: lm, selected: sel == MapSelection(MapSelKind.landmark, lm.id), onTap: () => select(MapSelection(MapSelKind.landmark, lm.id))),
            for (final slot in l.services)
              if (d.service(slot.id) case final s?)
                _ServicePin(
                  slot: slot,
                  s: s,
                  shadows: fx,
                  selected: sel == MapSelection(MapSelKind.service, slot.id),
                  onTap: () => select(MapSelection(MapSelKind.service, slot.id)),
                ),
            for (final m in l.districts)
              _DistrictNode(
                m: m,
                d: d,
                pulse: _pulse,
                shadows: fx,
                selected: sel == MapSelection(MapSelKind.district, '${m.id}'),
                onTap: () => widget.onDistrict != null ? widget.onDistrict!(m.id) : select(MapSelection(MapSelKind.district, '${m.id}')),
              ),
          ]),
        ),
      ),
    );
  }
}

/// Najmniejsza skala, przy której plansza pokrywa cały widok (bez pustych pasów).
double coverScale(Size view, MapLayout l) => math.max(view.width / l.width, view.height / l.height);

// ───────────────────────────── węzły
class _DistrictNode extends StatelessWidget {
  const _DistrictNode({required this.m, required this.d, required this.pulse, required this.selected, required this.onTap, this.shadows = true});
  final bool shadows;
  final MapDistrict m;
  final MapData d;
  final Animation<double> pulse;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final here = d.here == m.id;
    final open = d.isOpen(m.id);
    final target = d.travel?['to'] == m.id;
    final ring = selected ? AppColors.gold : (target ? AppColors.gold : (here ? AppColors.primary : AppColors.border));
    return Positioned(
      left: m.x - 60,
      top: m.y - 34,
      width: 120,
      child: GestureDetector(
        key: Key('node-${m.id}'),
        onTap: onTap,
        child: Column(children: [
          AnimatedBuilder(
            animation: pulse,
            builder: (_, child) => Container(
              width: 56,
              height: 56,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: here ? const Color(0xFF16345A) : AppColors.surface,
                border: Border.all(color: ring, width: here || selected || target ? 3 : 1.5),
                boxShadow: [
                  if (here) BoxShadow(color: AppColors.primary.withValues(alpha: .35 + .3 * pulse.value), blurRadius: 14 + 10 * pulse.value),
                  if (shadows) const BoxShadow(color: Color(0x66000000), blurRadius: 6, offset: Offset(0, 3)),
                ],
              ),
              child: child,
            ),
            child: Opacity(opacity: open ? 1 : .55, child: Text(m.icon, style: const TextStyle(fontSize: 26))),
          ),
          const SizedBox(height: 3),
          _Label(m.name, color: here ? AppColors.primary : (open ? AppColors.textPrimary : AppColors.textSecondary), bold: true),
          if (here)
            const _Tag('TU JESTEŚ', AppColors.primary)
          else if (!open)
            const _Tag('🔒 Era', AppColors.textSecondary),
        ]),
      ),
    );
  }
}

class _ServicePin extends StatelessWidget {
  const _ServicePin({required this.slot, required this.s, required this.selected, required this.onTap, this.shadows = true});
  final bool shadows;
  final MapServiceSlot slot;
  final MapService s;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final pct = s.demandPct;
    final c = demandColor(pct);
    return Positioned(
      left: slot.pos.dx - 58,
      top: slot.pos.dy - 16,
      width: 116,
      child: Center(
        child: GestureDetector(
          key: Key('pin-${slot.id}'),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.fromLTRB(5, 3, 7, 3),
            decoration: BoxDecoration(
              color: AppColors.surface.withValues(alpha: .94),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: selected ? AppColors.gold : c.withValues(alpha: .75), width: selected ? 2 : 1),
              boxShadow: shadows ? const [BoxShadow(color: Color(0x55000000), blurRadius: 4, offset: Offset(0, 2))] : null,
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(s.unlocked ? s.icon : '🔒', style: const TextStyle(fontSize: 15)),
              const SizedBox(width: 4),
              Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                Text('${demandBadge(pct)} $pct%', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: c, height: 1.1)),
                Text('${money(s.rateNow)}/h', style: const TextStyle(fontSize: 9, color: AppColors.textSecondary, height: 1.1)),
              ]),
            ]),
          ),
        ),
      ),
    );
  }
}

class _LandmarkNode extends StatelessWidget {
  const _LandmarkNode({required this.lm, required this.selected, required this.onTap});
  final MapLandmark lm;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: lm.pos.dx - 60,
      top: lm.pos.dy - 22,
      width: 120,
      child: GestureDetector(
        key: Key('landmark-${lm.id}'),
        onTap: onTap,
        child: Column(children: [
          Container(
            width: 38,
            height: 38,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.surface,
              border: Border.all(color: selected ? AppColors.gold : const Color(0xFF7DD3FC), width: selected ? 2.5 : 1.2),
            ),
            child: Text(lm.icon, style: const TextStyle(fontSize: 18)),
          ),
          _Label(lm.name, color: const Color(0xFF7DD3FC)),
        ]),
      ),
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text, {required this.color, this.bold = false});
  final String text;
  final Color color;
  final bool bold;
  @override
  Widget build(BuildContext context) => Text(
        text,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: bold ? 12.5 : 10.5,
          fontWeight: bold ? FontWeight.w800 : FontWeight.w700,
          color: color,
          shadows: const [Shadow(color: Colors.black, blurRadius: 4)],
        ),
      );
}

class _Tag extends StatelessWidget {
  const _Tag(this.text, this.color);
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 2),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(color: color.withValues(alpha: .18), borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: TextStyle(fontSize: 9, fontWeight: FontWeight.w900, color: color, letterSpacing: .5)),
      );
}

// ───────────────────────────── malarze
Path _poly(List<Offset> pts) {
  final p = Path();
  if (pts.isEmpty) return p;
  p.moveTo(pts.first.dx, pts.first.dy);
  for (final o in pts.skip(1)) {
    p.lineTo(o.dx, o.dy);
  }
  return p..close();
}

Path _smooth(List<Offset> pts) {
  final p = Path();
  if (pts.isEmpty) return p;
  p.moveTo(pts.first.dx, pts.first.dy);
  for (var i = 1; i < pts.length; i++) {
    final a = pts[i - 1], b = pts[i];
    final mid = Offset((a.dx + b.dx) / 2, (a.dy + b.dy) / 2);
    p.quadraticBezierTo(a.dx, a.dy, mid.dx, mid.dy);
  }
  p.lineTo(pts.last.dx, pts.last.dy);
  return p;
}

/// Statyczny teren (rysowany raz, RepaintBoundary): tło, regiony, morze, rzeki, jeziora, bagna, drogi, mosty.
class TerrainPainter extends CustomPainter {
  /// E5: [ground] = tło/regiony/woda, [roads] = drogi, mosty i podpisy — rozdzielone, by tekstury PNG weszły pomiędzy.
  TerrainPainter(this.l, {this.ground = true, this.roads = true});
  final MapLayout l;
  final bool ground, roads;
  static const _water = Color(0xFF123A66);

  @override
  void paint(Canvas canvas, Size size) {
    if (ground) _ground(canvas, size);
    if (roads) _roads(canvas, size);
  }

  void _ground(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = l.background);
    // delikatna siatka
    final grid = Paint()
      ..color = const Color(0xFF15233B)
      ..strokeWidth = 1;
    for (double x = 0; x <= size.width; x += 50) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), grid);
    }
    for (double y = 0; y <= size.height; y += 50) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    // regiony
    for (final r in l.regions) {
      final path = _poly(r.polygon);
      canvas.drawPath(path, Paint()..color = r.color.withValues(alpha: .85));
      canvas.drawPath(
          path,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.5
            ..color = Color.lerp(r.color, Colors.white, .25)!.withValues(alpha: .6));
    }
    // morze z jaśniejszą linią brzegu
    final sea = _poly(l.sea);
    canvas.drawPath(sea, Paint()..color = _water);
    canvas.drawPath(
        sea,
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 3
          ..color = const Color(0xFF3B82C4).withValues(alpha: .6));
    // rzeki
    for (final r in l.rivers) {
      canvas.drawPath(
          _smooth(r.points),
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round
            ..strokeJoin = StrokeJoin.round
            ..strokeWidth = r.width
            ..color = _water);
      canvas.drawPath(
          _smooth(r.points),
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round
            ..strokeWidth = math.max(1, r.width / 4)
            ..color = const Color(0xFF3B82C4).withValues(alpha: .5));
    }
    for (final o in l.lakes) {
      final rect = Rect.fromCenter(center: o.center, width: o.rx * 2, height: o.ry * 2);
      canvas.drawOval(rect, Paint()..color = _water);
      canvas.drawOval(
          rect,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2
            ..color = const Color(0xFF3B82C4).withValues(alpha: .6));
    }
    final swamp = Paint()..color = const Color(0xFF2D4A3A);
    for (final o in l.swamps) {
      canvas.drawOval(Rect.fromCenter(center: o.center, width: o.rx * 2, height: o.ry * 2), swamp);
      final dots = Paint()..color = const Color(0xFF4F7A5E);
      for (var i = 0; i < 14; i++) {
        final a = i * 2.4;
        canvas.drawCircle(o.center + Offset(math.cos(a) * o.rx * .6 * ((i % 3) / 3 + .3), math.sin(a) * o.ry * .6), 2, dots);
      }
    }
  }

  void _roads(Canvas canvas, Size size) {
    // drogi: obrys + jezdnia + przerywana linia środkowa
    for (final r in l.roads) {
      final a = l.district(r.a).pos, b = l.district(r.b).pos;
      final main = r.kind == 'main';
      canvas.drawLine(a, b, Paint()..color = const Color(0xFF0A1322)..strokeWidth = main ? 12 : 8..strokeCap = StrokeCap.round);
      canvas.drawLine(a, b, Paint()..color = const Color(0xFF3A4A66)..strokeWidth = main ? 8 : 5..strokeCap = StrokeCap.round);
      if (main) _dashed(canvas, a, b, Paint()..color = const Color(0xFFB8C4D9).withValues(alpha: .55)..strokeWidth = 1.2);
      _bridges(canvas, a, b); // E5: most wszędzie, gdzie droga przecina rzekę (nie tylko z flagą bridge)
    }
    // nazwy regionów
    for (final r in l.regions) {
      final tp = TextPainter(
        text: TextSpan(
          text: r.name.toUpperCase(),
          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, letterSpacing: 2, color: Colors.white.withValues(alpha: .38)),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, r.label);
    }
  }

  void _dashed(Canvas c, Offset a, Offset b, Paint p) {
    final len = (b - a).distance;
    final dir = (b - a) / len;
    for (double t = 10; t < len - 10; t += 14) {
      c.drawLine(a + dir * t, a + dir * math.min(t + 7, len - 10), p);
    }
  }

  /// Most = miejsce, gdzie droga przecina rzekę (przybliżenie: przecięcie z odcinkami rzeki).
  void _bridges(Canvas c, Offset a, Offset b) {
    for (final r in l.rivers) {
      for (var i = 1; i < r.points.length; i++) {
        final x = _intersect(a, b, r.points[i - 1], r.points[i]);
        if (x == null) continue;
        final dir = (b - a) / (b - a).distance;
        final n = Offset(-dir.dy, dir.dx);
        // E5: wyraźny most — cień na wodzie, pomost z deskami, filary i złote barierki
        final half = r.width / 2 + 9;
        Offset q(double along, double side) => x + dir * along + n * side;
        final deck = Path()..addPolygon([q(-half, -6), q(half, -6), q(half, 6), q(-half, 6)], true);
        c.drawPath(deck.shift(const Offset(1.5, 3)), Paint()..color = const Color(0x88000000));
        c.drawPath(deck, Paint()..color = const Color(0xFF5B4632));
        final plank = Paint()
          ..color = const Color(0xFF3B2D20)
          ..strokeWidth = 1;
        for (double t = -half + 3; t < half; t += 3.5) {
          c.drawLine(q(t, -5.5), q(t, 5.5), plank);
        }
        final rail = Paint()
          ..color = const Color(0xFFC9A227)
          ..strokeWidth = 1.8;
        for (final s in [-6.5, 6.5]) {
          c.drawLine(q(-half - 3, s), q(half + 3, s), rail);
          for (double t = -half; t <= half; t += half / 2) {
            c.drawCircle(q(t, s), 1.5, Paint()..color = const Color(0xFFE8C547));
          }
        }
      }
    }
  }

  Offset? _intersect(Offset p1, Offset p2, Offset p3, Offset p4) {
    final d = (p2.dx - p1.dx) * (p4.dy - p3.dy) - (p2.dy - p1.dy) * (p4.dx - p3.dx);
    if (d.abs() < 1e-6) return null;
    final u = ((p3.dx - p1.dx) * (p4.dy - p3.dy) - (p3.dy - p1.dy) * (p4.dx - p3.dx)) / d;
    final v = ((p3.dx - p1.dx) * (p2.dy - p1.dy) - (p3.dy - p1.dy) * (p2.dx - p1.dx)) / d;
    if (u < 0 || u > 1 || v < 0 || v > 1) return null;
    return p1 + (p2 - p1) * u;
  }

  @override
  bool shouldRepaint(covariant TerrainPainter old) => old.l != l;
}

/// Trasa trwającej podróży gracza (złota, przerywana).
class RoutePainter extends CustomPainter {
  RoutePainter(this.l, this.here, this.travel);
  final MapLayout l;
  final int here;
  final Map<String, dynamic>? travel;
  @override
  void paint(Canvas canvas, Size size) {
    final t = travel;
    if (t == null) return;
    final a = l.district(here).pos;
    final b = l.district((t['to'] as num?)?.toInt() ?? here).pos;
    canvas.drawLine(a, b, Paint()..color = AppColors.gold..strokeWidth = 4..strokeCap = StrokeCap.round);
  }

  @override
  bool shouldRepaint(covariant RoutePainter old) => old.here != here || old.travel != travel;
}

/// Nocne światła miast i usług (blask zależny od nightFactor, delikatne pulsowanie).
class GlowPainter extends CustomPainter {
  GlowPainter(this.l, this.night, this.pulse);
  final MapLayout l;
  final double night, pulse;
  @override
  void paint(Canvas canvas, Size size) {
    void glow(Offset c, double r, Color color, double a) {
      canvas.drawCircle(
        c,
        r,
        Paint()
          ..shader = ui.Gradient.radial(c, r, [color.withValues(alpha: a * night), color.withValues(alpha: 0)])
          ..blendMode = BlendMode.plus,
      );
    }

    for (final m in l.districts) {
      final big = m.kind == 'city';
      glow(m.pos, (big ? 95 : 65) + 6 * pulse, const Color(0xFFFFC56B), big ? .42 : .3);
      // okna: kilka drobnych świateł wokół miasta
      final rnd = math.Random(m.id * 7);
      for (var i = 0; i < (big ? 14 : 7); i++) {
        final o = m.pos + Offset((rnd.nextDouble() - .5) * 120, (rnd.nextDouble() - .5) * 80);
        final flick = .6 + .4 * math.sin(pulse * math.pi * 2 + i);
        canvas.drawCircle(o, 1.6, Paint()..color = const Color(0xFFFFE2A0).withValues(alpha: .85 * night * flick));
      }
    }
    for (final s in l.services) {
      glow(s.pos, 34, const Color(0xFF4AA8FF), .35);
    }
    for (final lm in l.landmarks) {
      glow(lm.pos, 40, const Color(0xFF7DD3FC), .35);
    }
  }

  @override
  bool shouldRepaint(covariant GlowPainter old) => old.night != night || old.pulse != pulse;
}
