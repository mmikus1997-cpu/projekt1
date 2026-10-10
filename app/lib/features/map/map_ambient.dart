import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'map_layout.dart';

/// UI v2 Etap 5: drobne „życie” mapy — sarna w Lasach Wschodnich, łódka na morzu, dym z kominów.
/// Konfiguracja w map_data.json → "ambient". Czysty CustomPaint (bez pakietów cząsteczek).
/// Wydajność: jeden Ticker; stoi, gdy [enabled] = false (Eco / oszczędzanie baterii / ograniczenie ruchu w systemie)
/// albo gdy żaden efekt nie jest w kadrze (gracz przewinął mapę gdzie indziej).
class AmbientLayer extends StatefulWidget {
  const AmbientLayer({super.key, required this.layout, required this.view, required this.viewport, required this.enabled});
  final MapLayout layout;
  final TransformationController view;
  final Size viewport;
  final bool enabled;
  @override
  State<AmbientLayer> createState() => _AmbientLayerState();
}

class _Ambient {
  _Ambient(MapLayout l) {
    final a = (l.j['ambient'] as Map?) ?? const {};
    List<Offset> pts(Object? v) => [for (final p in (v as List?) ?? const []) if (p is List) Offset((p[0] as num).toDouble(), (p[1] as num).toDouble())];
    deer = pts((a['deer'] as Map?)?['path']);
    boat = pts((a['boat'] as Map?)?['path']);
    chimneys = pts(a['chimneys']);
    art = l.artAsset != null;
    // M4: ruch uliczny w tle — auta krążą po drogach namalowanych na grafice (roads[].path)
    roads = [
      for (final r in (l.j['roads'] as List?) ?? const [])
        if (r is Map && r['path'] is List) _Poly(pts(r['path'])),
    ];
    Rect box(List<Offset> p, double pad) => p.isEmpty
        ? Rect.zero
        : Rect.fromPoints(
            Offset(p.map((e) => e.dx).reduce(math.min), p.map((e) => e.dy).reduce(math.min)),
            Offset(p.map((e) => e.dx).reduce(math.max), p.map((e) => e.dy).reduce(math.max)),
          ).inflate(pad);
    bounds = [box(deer, 20), box(boat, 20), box(chimneys, 50).translate(0, -25), for (final r in roads) box(r.p, 12)].where((r) => r != Rect.zero).toList();
  }
  late final List<Offset> deer, boat, chimneys;
  late final List<_Poly> roads;
  late final bool art;
  late final List<Rect> bounds;
}

class _AmbientLayerState extends State<AmbientLayer> with SingleTickerProviderStateMixin {
  late final AnimationController _tick = AnimationController(vsync: this, duration: const Duration(seconds: 1))..addListener(_frame);
  // dym/łódka/sarna nie potrzebują 60 FPS — repaint ograniczony do ~24 FPS (o ~60% mniej pracy rasteryzacji)
  final _repaint = ValueNotifier<int>(0);
  int _last = 0;
  void _frame() {
    final ms = _clock.elapsedMilliseconds;
    if (ms - _last >= 41) {
      _last = ms;
      _repaint.value++;
    }
  }
  final _clock = Stopwatch()..start();
  late _Ambient _a = _Ambient(widget.layout);
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    widget.view.addListener(_onView);
    WidgetsBinding.instance.addPostFrameCallback((_) => _sync());
  }

  @override
  void didUpdateWidget(covariant AmbientLayer old) {
    super.didUpdateWidget(old);
    if (old.view != widget.view) {
      old.view.removeListener(_onView);
      widget.view.addListener(_onView);
    }
    if (old.layout != widget.layout) _a = _Ambient(widget.layout);
    _sync();
  }

  // przesuwanie mapy generuje dziesiątki zdarzeń/s — sprawdzamy widoczność z lekkim opóźnieniem
  void _onView() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 120), _sync);
  }

  Rect _visible() => MatrixUtils.inverseTransformRect(widget.view.value, Offset.zero & widget.viewport);

  void _sync() {
    if (!mounted) return;
    final motionOk = !(MediaQuery.maybeDisableAnimationsOf(context) ?? false);
    final vis = _visible();
    final run = widget.enabled && motionOk && _a.bounds.any(vis.overlaps);
    if (run && !_tick.isAnimating) _tick.repeat();
    if (!run && _tick.isAnimating) _tick.stop(); // Ticker zatrzymany = zero klatek
  }

  @override
  void dispose() {
    widget.view.removeListener(_onView);
    _debounce?.cancel();
    _tick.dispose();
    _repaint.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: RepaintBoundary(
          child: CustomPaint(
            key: Key(widget.enabled ? 'map-ambient-on' : 'map-ambient-off'),
            painter: _AmbientPainter(_a, _repaint, () => _clock.elapsedMilliseconds / 1000, widget.enabled, _visible),
            size: Size(widget.layout.width, widget.layout.height),
          ),
        ),
      );
}

/// Polilinia z parametryzacją po długości (stała prędkość aut na zakrętach).
class _Poly {
  _Poly(this.p) {
    var acc = 0.0;
    cum.add(0);
    for (var i = 1; i < p.length; i++) {
      acc += (p[i] - p[i - 1]).distance;
      cum.add(acc);
    }
  }
  final List<Offset> p;
  final cum = <double>[];
  double get length => cum.last;
  /// pozycja i kierunek w odległości [d] od początku
  (Offset, Offset) at(double d) {
    for (var i = 1; i < p.length; i++) {
      if (d <= cum[i]) {
        final seg = cum[i] - cum[i - 1];
        final dir = seg == 0 ? const Offset(1, 0) : (p[i] - p[i - 1]) / seg;
        return (Offset.lerp(p[i - 1], p[i], seg == 0 ? 0 : (d - cum[i - 1]) / seg)!, dir);
      }
    }
    return (p.last, const Offset(1, 0));
  }
}

const _carColors = [Color(0xFFE11D48), Color(0xFFF8FAFC), Color(0xFF2563EB), Color(0xFFFACC15), Color(0xFF16A34A), Color(0xFF111827)];

class _AmbientPainter extends CustomPainter {
  _AmbientPainter(this.a, Listenable tick, this.time, this.enabled, this.visible) : super(repaint: tick);
  final _Ambient a;
  final double Function() time;
  final bool enabled;
  final Rect Function() visible;

  static Offset _along(List<Offset> p, double t) {
    if (p.length < 2) return p.isEmpty ? Offset.zero : p.first;
    final f = t.clamp(0.0, 1.0) * (p.length - 1);
    final i = math.min(f.floor(), p.length - 2);
    return Offset.lerp(p[i], p[i + 1], f - i)!;
  }

  @override
  void paint(Canvas c, Size size) {
    final s = time();
    final vis = visible().inflate(40);
    // kominy rysujemy zawsze (statyczne) — dym tylko z włączonymi efektami
    final chim = Paint()..color = const Color(0xFF4A3B33);
    final cap = Paint()..color = const Color(0xFFB45309);
    for (var i = 0; i < a.chimneys.length; i++) {
      final p = a.chimneys[i];
      if (!a.art) {
        // kominy są już na malowanej grafice — rysujemy tylko dym
        c.drawRect(Rect.fromLTWH(p.dx - 3, p.dy - 2, 6, 16), chim);
        c.drawRect(Rect.fromLTWH(p.dx - 3.5, p.dy - 2, 7, 2.5), cap);
      }
      if (!enabled || !vis.contains(p)) continue;
      for (var k = 0; k < 5; k++) {
        final ph = ((s * .22 + k / 5 + i * .37) % 1.0);
        final o = p + Offset(math.sin(ph * 5 + i) * 4 + ph * 10, -ph * 42);
        c.drawCircle(o, 3 + ph * 7, Paint()..color = Color.fromRGBO(190, 196, 206, .38 * (1 - ph)));
      }
    }
    if (!enabled) return; // Eco: bez łódki, sarny i ruchu ulicznego
    // ruch uliczny: 2 auta na drogę, w przeciwnych kierunkach, na swoich pasach (~26 px/s)
    for (var i = 0; i < a.roads.length; i++) {
      final r = a.roads[i];
      if (r.length < 20) continue;
      for (var k = 0; k < 2; k++) {
        final dist = ((s * 26 + i * 97 + k * r.length / 2) % r.length);
        final fwd = k == 0;
        final (pos, dir) = r.at(fwd ? dist : r.length - dist);
        final d = fwd ? dir : -dir;
        final p = pos + Offset(-d.dy, d.dx) * 3.2; // ruch prawostronny
        if (vis.contains(p)) _car(c, p, d, _carColors[(i * 2 + k) % _carColors.length]);
      }
    }
    // łódka: tam i z powrotem w 70 s
    if (a.boat.length >= 2) {
      final cyc = (s / 70) % 1.0;
      final fwd = cyc < .5;
      final t = fwd ? cyc * 2 : (1 - cyc) * 2;
      final p = _along(a.boat, t);
      if (vis.contains(p)) _boat(c, p, fwd ? 1 : -1, s);
    }
    // sarna: przebiega co 18 s przez 4 s
    if (a.deer.length >= 2) {
      final cyc = s % 18;
      if (cyc < 4) {
        final t = cyc / 4;
        final p = _along(a.deer, t);
        final next = _along(a.deer, math.min(1, t + .02));
        if (vis.contains(p)) _deer(c, p, next.dx >= p.dx ? 1 : -1, s, math.min(1, math.min(t, 1 - t) * 6));
      }
    }
  }

  void _car(Canvas c, Offset p, Offset dir, Color color) {
    c.save();
    c.translate(p.dx, p.dy);
    c.rotate(math.atan2(dir.dy, dir.dx));
    c.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(-5, -2.2, 11, 6), const Radius.circular(2)), Paint()..color = const Color(0x55000000));
    c.drawRRect(RRect.fromRectAndRadius(const Rect.fromLTWH(-5.5, -3, 11, 6), const Radius.circular(2)), Paint()..color = color);
    c.drawRect(const Rect.fromLTWH(1, -2.2, 2.6, 4.4), Paint()..color = const Color(0xCC93C5FD)); // przednia szyba
    c.restore();
  }

  void _boat(Canvas c, Offset p, double dir, double s) {
    final bob = math.sin(s * 2) * .8;
    final wake = Paint()
      ..color = const Color(0x66BFDBFE)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    for (var k = 1; k <= 3; k++) {
      c.drawLine(p + Offset(-dir * (8 + k * 5), 2 + k * .8), p + Offset(-dir * (12 + k * 6), 4 + k * 1.6), wake);
      c.drawLine(p + Offset(-dir * (8 + k * 5), 2 - k * .2), p + Offset(-dir * (12 + k * 6), 1 - k * .6), wake);
    }
    final q = p + Offset(0, bob);
    final hull = Path()
      ..moveTo(q.dx - 9 * dir, q.dy)
      ..lineTo(q.dx + 11 * dir, q.dy)
      ..lineTo(q.dx + 7 * dir, q.dy + 4)
      ..lineTo(q.dx - 7 * dir, q.dy + 4)
      ..close();
    c.drawPath(hull, Paint()..color = const Color(0xFF7C4A2D));
    final sail = Path()
      ..moveTo(q.dx, q.dy - 1)
      ..lineTo(q.dx, q.dy - 14)
      ..lineTo(q.dx + 8 * dir, q.dy - 2)
      ..close();
    c.drawPath(sail, Paint()..color = const Color(0xFFF1F5F9));
  }

  /// Cień sarny: sylwetka z animowanymi nogami, półprzezroczysta.
  void _deer(Canvas c, Offset p, double dir, double s, double alpha) {
    final ink = Paint()
      ..color = Color.fromRGBO(8, 14, 10, .7 * alpha)
      ..strokeWidth = 1.6
      ..strokeCap = StrokeCap.round;
    c.drawOval(Rect.fromCenter(center: p + const Offset(0, 9), width: 18, height: 4), Paint()..color = Color.fromRGBO(0, 0, 0, .25 * alpha));
    c.drawOval(Rect.fromCenter(center: p, width: 14, height: 6), ink);
    final neck = p + Offset(6 * dir, -2);
    final head = p + Offset(9 * dir, -7);
    c.drawLine(neck, head, ink..strokeWidth = 2.4);
    c.drawCircle(head, 2.2, ink);
    ink.strokeWidth = 1;
    c.drawLine(head, head + Offset(-1 * dir, -5), ink);
    c.drawLine(head + Offset(-1 * dir, -3), head + Offset(-3 * dir, -5), ink);
    ink.strokeWidth = 1.4;
    final g = math.sin(s * 18) * 3; // galop
    for (final (x, ph) in [(-5.0, 1.0), (-3.0, -1.0), (4.0, -1.0), (6.0, 1.0)]) {
      final top = p + Offset(x * dir, 2);
      c.drawLine(top, top + Offset(g * ph * dir, 7), ink);
    }
  }

  @override
  bool shouldRepaint(covariant _AmbientPainter old) => old.enabled != enabled || old.a != a;
}
