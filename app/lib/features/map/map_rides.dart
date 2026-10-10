import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../shared/models/models.dart';
import 'map_layout.dart';

/// UI v2 Etap 4: auta NPC jadące po drogach mapy (Rezydencja ⇄ usługa).
/// Pozycja = interpolacja po trasie wg (teraz − wyjazd) / (przyjazd − wyjazd).
/// Wydajność: jeden Ticker → CustomPainter(repaint:), bez rebuildów; Ticker stoi, gdy żaden kurs nie jest w kadrze.
class RidesLayer extends StatefulWidget {
  const RidesLayer({super.key, required this.layout, required this.rides, required this.view, required this.viewport, this.animate = true, this.clockOffsetMs = 0});
  final MapLayout layout;
  /// E5: false (Tryb Eco) = bez animacji pojazdów, zostaje sama linia trasy.
  final bool animate;
  final int clockOffsetMs;
  final List<NpcRide> rides;
  final TransformationController view;
  final Size viewport;
  @override
  State<RidesLayer> createState() => _RidesLayerState();
}

class _RidesLayerState extends State<RidesLayer> with SingleTickerProviderStateMixin {
  late final AnimationController _tick = AnimationController(vsync: this, duration: const Duration(seconds: 1));
  Timer? _check;
  late List<_Route> _routes;

  @override
  void initState() {
    super.initState();
    _build();
    widget.view.addListener(_sync);
    // kursy kończą się/zaczynają w czasie — sprawdzenie widoczności co 2 s
    _check = Timer.periodic(const Duration(seconds: 2), (_) => _sync());
    _sync();
  }

  @override
  void didUpdateWidget(covariant RidesLayer old) {
    super.didUpdateWidget(old);
    if (old.view != widget.view) {
      old.view.removeListener(_sync);
      widget.view.addListener(_sync);
    }
    if (old.rides != widget.rides || old.layout != widget.layout) _build();
    _sync();
  }

  void _build() {
    _routes = [
      for (final r in widget.rides)
        if (widget.layout.ridePoints(r.serviceId, toWork: r.toWork) case final pts when pts.length >= 2) _Route(r, pts),
    ];
  }

  /// Widoczny fragment planszy (odwrotność transformacji InteractiveViewer).
  Rect _visible() => MatrixUtils.inverseTransformRect(widget.view.value, Offset.zero & widget.viewport).inflate(60);

  void _sync() {
    if (!mounted) return;
    final now = DateTime.now().millisecondsSinceEpoch + widget.clockOffsetMs;
    final vis = _visible();
    final any = widget.animate && _routes.any((r) => r.ride.arriveAt > now && vis.contains(r.at(r.ride.progress(now))));
    if (any && !_tick.isAnimating) _tick.repeat();
    if (!any && _tick.isAnimating) _tick.stop();
  }

  @override
  void dispose() {
    widget.view.removeListener(_sync);
    _check?.cancel();
    _tick.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: CustomPaint(
          key: const Key('map-rides'),
          painter: _RidesPainter(_routes, _tick, _visible, widget.animate, widget.clockOffsetMs),
          size: Size(widget.layout.width, widget.layout.height),
        ),
      );
}

class _Route {
  _Route(this.ride, this.pts) {
    var acc = 0.0;
    cum.add(0);
    for (var i = 1; i < pts.length; i++) {
      acc += (pts[i] - pts[i - 1]).distance;
      cum.add(acc);
    }
  }
  final NpcRide ride;
  final List<Offset> pts;
  final cum = <double>[];
  double get length => cum.last;

  Offset at(double t) {
    final d = length * t;
    for (var i = 1; i < pts.length; i++) {
      if (d <= cum[i]) {
        final seg = cum[i] - cum[i - 1];
        return Offset.lerp(pts[i - 1], pts[i], seg == 0 ? 0 : (d - cum[i - 1]) / seg)!;
      }
    }
    return pts.last;
  }
}

class _RidesPainter extends CustomPainter {
  _RidesPainter(this.routes, Listenable tick, this.visible, this.animate, this.clockOffsetMs) : super(repaint: tick);
  final bool animate;
  final int clockOffsetMs;
  final List<_Route> routes;
  final Rect Function() visible;
  static final _text = <String, TextPainter>{};

  TextPainter _tp(String s, double size, Color c) => _text.putIfAbsent('$s|$size|${c.toARGB32()}', () {
        return TextPainter(
          text: TextSpan(text: s, style: TextStyle(fontSize: size, fontWeight: FontWeight.w800, color: c, shadows: const [Shadow(blurRadius: 3)])),
          textDirection: TextDirection.ltr,
        )..layout();
      });

  @override
  void paint(Canvas c, Size size) {
    final now = DateTime.now().millisecondsSinceEpoch + clockOffsetMs;
    final vis = visible();
    for (final r in routes) {
      final ride = r.ride;
      if (ride.arriveAt <= now) continue;
      final t = ride.progress(now);
      final p = r.at(t);
      if (animate && !vis.contains(p)) continue; // poza kadrem — nie rysujemy (Eco: statyczna linia zawsze)
      final (color, icon) = switch (ride.transport) {
        'bus' => (const Color(0xFFF59E0B), '🚌'),
        'hitchhike' => (AppColors.success, '👍'),
        _ => (AppColors.primary, '🚗'),
      };
      // ślad trasy (przerywany)
      final trail = Paint()
        ..color = color.withValues(alpha: .35)
        ..strokeWidth = 2;
      for (double d = 0; d < r.length; d += 12) {
        c.drawLine(r.at(d / r.length), r.at(math.min(d + 6, r.length) / r.length), trail);
      }
      if (!animate) continue; // Eco: tylko linia trasy
      // pojazd
      c.drawCircle(p, 11, Paint()..color = const Color(0xE60B1220));
      c.drawCircle(p, 11, Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2);
      final ic = _tp(icon, 12, Colors.white);
      ic.paint(c, p - Offset(ic.width / 2, ic.height / 2));
      // malutka etykieta: imię + pasek postępu kursu
      final lb = _tp(ride.name, 8.5, Colors.white);
      final top = p + Offset(-math.max(lb.width, 28) / 2, -27);
      c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(top.dx - 3, top.dy - 1, math.max(lb.width, 28) + 6, 15), const Radius.circular(4)),
          Paint()..color = const Color(0xCC0B1220));
      lb.paint(c, top + Offset((math.max(lb.width, 28) - lb.width) / 2, 0));
      final bar = Rect.fromLTWH(top.dx, top.dy + 10.5, math.max(lb.width, 28), 2.2);
      c.drawRect(bar, Paint()..color = Colors.white24);
      c.drawRect(Rect.fromLTWH(bar.left, bar.top, bar.width * t, bar.height), Paint()..color = color);
    }
  }

  @override
  bool shouldRepaint(covariant _RidesPainter old) => old.routes != routes || old.animate != animate || old.clockOffsetMs != clockOffsetMs;
}
