import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import 'district_providers.dart';

/// UI v2 Etap 3: wizualny plan Dzielnicy — 4 etapy rozwoju wg sumy poziomów 6 budynków (max 29).
/// Malowane budynki: wspólna perspektywa frontalna z góry, bez osobnych podestów.
int districtStage(int total) => total < 5 ? 1 : (total <= 15 ? 2 : (total <= 25 ? 3 : 4));
const stageNames = {1: 'Pustkowie', 2: 'Plac Budowy', 3: 'Zorganizowany Hub', 4: 'Metropolia'};

/// Podgląd etapu (null = wg realnych poziomów) — tylko widok, nic nie zmienia w grze.
final districtStagePreviewProvider = StateProvider<int?>((_) => null);

/// Plan 1000×560 (wirtualne px): pozycja i rozmiar parceli każdego budynku.
const _plots = <String, Rect>{
  'residence': Rect.fromLTWH(90, 70, 250, 180),
  'garage': Rect.fromLTWH(90, 320, 220, 160),
  'cafe': Rect.fromLTWH(420, 80, 170, 140),
  'nightclub': Rect.fromLTWH(640, 70, 200, 160),
  'club': Rect.fromLTWH(420, 320, 230, 170),
  'hall': Rect.fromLTWH(720, 310, 200, 190),
};

// Podkłady etapów 3–4 mają parcele namalowane w nieco innym miejscu niż szkic (plan 1000×560) —
// korekty zmierzone na ground_3/ground_4.jpg, żeby budynek stał na swoim placu, a nie na ulicy.
const _plotsByStage = <int, Map<String, Rect>>{
  1: {
    'residence': Rect.fromLTWH(95, 65, 225, 164),
    'cafe': Rect.fromLTWH(427, 64, 157, 150),
    'nightclub': Rect.fromLTWH(645, 65, 190, 160),
    'garage': Rect.fromLTWH(91, 330, 215, 145),
    'club': Rect.fromLTWH(430, 330, 200, 155),
    'hall': Rect.fromLTWH(726, 330, 185, 160),
  },
  2: {
    'residence': Rect.fromLTWH(94, 76, 240, 164),
    'cafe': Rect.fromLTWH(426, 86, 164, 129),
    'nightclub': Rect.fromLTWH(647, 75, 190, 146),
    'garage': Rect.fromLTWH(98, 330, 203, 141),
    'club': Rect.fromLTWH(430, 331, 209, 141),
    'hall': Rect.fromLTWH(729, 324, 185, 160),
  },
  3: {
    'residence': Rect.fromLTWH(95, 49, 226, 154),
    'cafe': Rect.fromLTWH(431, 52, 150, 150),
    'nightclub': Rect.fromLTWH(654, 45, 177, 160),
    'garage': Rect.fromLTWH(101, 340, 200, 166),
    'club': Rect.fromLTWH(431, 340, 208, 166),
    'hall': Rect.fromLTWH(778, 347, 130, 163),
  },
  4: {
    'residence': Rect.fromLTWH(114, 83, 188, 136),
    'cafe': Rect.fromLTWH(436, 84, 139, 132),
    'nightclub': Rect.fromLTWH(660, 88, 161, 137),
    'garage': Rect.fromLTWH(117, 338, 180, 127),
    'club': Rect.fromLTWH(437, 340, 188, 141),
    'hall': Rect.fromLTWH(741, 340, 155, 153),
  },
};

Rect? plotFor(int stage, String id) => _plotsByStage[stage]?[id] ?? _plots[id];

class DistrictVisual extends ConsumerStatefulWidget {
  const DistrictVisual({super.key, required this.d, required this.onTap});
  final DistrictData d;
  final void Function(String buildingId) onTap;
  @override
  ConsumerState<DistrictVisual> createState() => _DistrictVisualState();
}

class _DistrictVisualState extends ConsumerState<DistrictVisual> with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(vsync: this, duration: const Duration(seconds: 3))..repeat();

  @override
  void dispose() {
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final total = d.buildings.fold<int>(0, (s, b) => s + b.level);
    final realStage = districtStage(total);
    final stage = ref.watch(districtStagePreviewProvider) ?? realStage;
    final mobile = MediaQuery.sizeOf(context).width < 600;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Container(
          key: const Key('district-visual'),
          decoration: BoxDecoration(border: Border.all(color: AppColors.border), borderRadius: BorderRadius.circular(18)),
          child: AspectRatio(
            aspectRatio: 1000 / 560,
            child: FittedBox(
              fit: BoxFit.contain, // cały plan widoczny na każdej szerokości
              child: SizedBox(
                width: 1000,
                height: 560,
                child: Stack(clipBehavior: Clip.none, children: [
                  // M5: malowany podkład etapu (brak pliku → dotychczasowy teren wektorowy)
                  Positioned.fill(
                    child: RepaintBoundary(
                      child: Image.asset('assets/images/district/ground_$stage.jpg',
                          key: Key('district-ground-$stage'),
                          fit: BoxFit.fill,
                          filterQuality: FilterQuality.medium,
                          errorBuilder: (_, _, _) => CustomPaint(painter: _GroundPainter(stage))),
                    ),
                  ),
                  for (final b in d.buildings)
                    if (plotFor(stage, b.id) case final r?)
                      Positioned.fromRect(
                        rect: r,
                        child: _BuildingObject(
                          b: b,
                          cons: d.construction?.building == b.id ? d.construction : null,
                          stage: stage,
                          anim: _t,
                          ready: (d.vault(b.id)?.amount ?? 0) >= 1,
                          full: (d.vault(b.id)?.fill ?? 0) >= 1,
                          onTap: () => widget.onTap(b.id),
                        ),
                      ),
                  // pasek etapu
                  Positioned(
                    left: 16,
                    top: 12,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(color: const Color(0xCC0B1220), borderRadius: BorderRadius.circular(12), border: Border.all(color: AppColors.border)),
                      child: Text('Etap $stage/4 · ${stageNames[stage]}',
                          key: const Key('district-stage'), style: TextStyle(fontSize: mobile ? 26 : 18, fontWeight: FontWeight.w900)),
                    ),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
      const SizedBox(height: 8),
      _StageProgress(total: total, realStage: realStage),
    ]);
  }
}

class _StageProgress extends ConsumerWidget {
  const _StageProgress({required this.total, required this.realStage});
  final int total, realStage;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preview = ref.watch(districtStagePreviewProvider);
    final next = switch (realStage) { 1 => 5, 2 => 16, 3 => 26, _ => null };
    return Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 6, runSpacing: 6, children: [
      Text('Suma poziomów $total/29 · ', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
      Text(next == null ? '🏆 Pełna Metropolia!' : '⬆️ Do etapu ${realStage + 1} (${stageNames[realStage + 1]}): jeszcze ${next - total} poz.',
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, fontWeight: FontWeight.w700)),
      const SizedBox(width: 6),
      const Text('Podgląd:', style: TextStyle(fontSize: 11, color: AppColors.textSecondary)),
      for (final s in [null, 1, 2, 3, 4])
        ChoiceChip(
          key: Key('stage-preview-${s ?? 'auto'}'),
          visualDensity: VisualDensity.compact,
          showCheckmark: false,
          label: Text(s == null ? 'Mój' : '$s', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
          selected: preview == s,
          onSelected: (_) => ref.read(districtStagePreviewProvider.notifier).state = s,
        ),
    ]);
  }
}

/// M5: wtopienie grafiki w podkład — miękki cień kontaktowy pod budynkiem + korekta barw pod paletę etapu
/// (Pustkowie cieplej i mniej nasycone, Metropolia prawie bez zmian). Opcjonalnie rusztowania (rozbudowa).
class _Blend extends StatelessWidget {
  const _Blend({required this.stage, required this.child, this.scaffold = false});
  final int stage;
  final Widget child;
  final bool scaffold;

  static List<double> _matrix(double sat, double r, double g, double b) {
    const lr = .2126, lg = .7152, lb = .0722;
    List<double> row(double m, int i) => [
          ((1 - sat) * lr + (i == 0 ? sat : 0)) * m,
          ((1 - sat) * lg + (i == 1 ? sat : 0)) * m,
          ((1 - sat) * lb + (i == 2 ? sat : 0)) * m,
          0,
          0,
        ];
    return [...row(r, 0), ...row(g, 1), ...row(b, 2), 0, 0, 0, 1, 0];
  }

  @override
  Widget build(BuildContext context) {
    final m = switch (stage) {
      1 => _matrix(.78, 1.0, .95, .82),
      2 => _matrix(.88, 1.0, .97, .9),
      3 => _matrix(.95, .98, 1.0, .96),
      _ => _matrix(1.0, 1.0, .99, .95),
    };
    final shade = scaffold ? _matrix(.55, .92, .9, .88) : m; // w budowie: przygaszony
    return Stack(clipBehavior: Clip.none, fit: StackFit.expand, children: [
      // cień kontaktowy — budynek „stoi” na placu zamiast na nim leżeć
      Positioned(
        left: 8,
        right: 8,
        bottom: -2,
        height: 16,
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: RadialGradient(colors: [Colors.black.withValues(alpha: stage == 1 ? .24 : .20), Colors.transparent], stops: const [.15, 1]),
            borderRadius: BorderRadius.circular(100),
          ),
        ),
      ),
      ColorFiltered(colorFilter: ColorFilter.matrix(shade), child: child),
      if (scaffold) const IgnorePointer(child: CustomPaint(painter: _ScaffoldPainter())),
    ]);
  }
}

/// Rusztowania rysowane na budynku w trakcie rozbudowy: stalowe słupy, pomosty z desek, stężenia, siatka.
class _ScaffoldPainter extends CustomPainter {
  const _ScaffoldPainter();
  @override
  void paint(Canvas c, Size s) {
    final l = s.width * .1, r = s.width * .9, t = s.height * .18, b = s.height * .9;
    final net = Paint()..color = const Color(0x3346A35A);
    c.drawRect(Rect.fromLTRB(l, t, l + (r - l) * .45, b), net); // zielona siatka ochronna z lewej
    final pole = Paint()
      ..color = const Color(0xFF8A939C)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    final dark = Paint()
      ..color = const Color(0xAA1B1F24)
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round;
    const cols = 5, rows = 4;
    final xs = [for (var i = 0; i < cols; i++) l + (r - l) * i / (cols - 1)];
    final ys = [for (var j = 0; j < rows; j++) t + (b - t) * j / (rows - 1)];
    for (final x in xs) {
      c.drawLine(Offset(x, t - 6), Offset(x, b), dark);
      c.drawLine(Offset(x, t - 6), Offset(x, b), pole);
    }
    final plank = Paint()..color = const Color(0xFFC08A4A);
    final plankEdge = Paint()
      ..color = const Color(0xFF6B4423)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    for (final y in ys.skip(1)) {
      final rr = Rect.fromLTRB(l - 4, y - 4, r + 4, y + 3);
      c.drawRect(rr, plank);
      c.drawRect(rr, plankEdge);
    }
    final brace = Paint()
      ..color = const Color(0xCC8A939C)
      ..strokeWidth = 2;
    for (var i = 0; i < cols - 1; i++) {
      for (var j = 0; j < rows - 1; j++) {
        final a = Offset(xs[i], ys[j]), z = Offset(xs[i + 1], ys[j + 1]);
        c.drawLine((i + j).isEven ? a : Offset(z.dx, a.dy), (i + j).isEven ? z : Offset(a.dx, z.dy), brace);
      }
    }
    // pachołki przy wejściu
    final cone = Paint()..color = const Color(0xFFFF7A1A);
    for (final x in [l + 6, r - 6]) {
      c.drawPath(Path()
        ..moveTo(x, b - 14)
        ..lineTo(x - 6, b + 2)
        ..lineTo(x + 6, b + 2)
        ..close(), cone);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

/// M5: pigułka z paskiem postępu i odliczaniem; po zakończeniu sama odświeża dane dzielnicy.
class ConstructionPill extends ConsumerStatefulWidget {
  const ConstructionPill({super.key, required this.c, this.wide = false});
  final Construction c;
  final bool wide;
  @override
  ConsumerState<ConstructionPill> createState() => _ConstructionPillState();
}

class _ConstructionPillState extends ConsumerState<ConstructionPill> {
  Timer? _t;
  bool _refreshed = false;
  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {});
      if (widget.c.done && !_refreshed) {
        _refreshed = true;
        Future.delayed(const Duration(milliseconds: 800), () {
          if (mounted) ref.invalidate(districtProvider);
        });
      }
    });
  }

  @override
  void didUpdateWidget(covariant ConstructionPill oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.c.building != widget.c.building || oldWidget.c.endsAt != widget.c.endsAt) {
      _refreshed = false;
    }
  }

  @override
  void dispose() {
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.c;
    final done = c.done;
    final text = done ? 'Potwierdzanie…' : '🏗️ ${fmtLeft(c.left())}';
    return Container(
      key: const Key('construction-pill'),
      width: widget.wide ? double.infinity : 150,
      padding: const EdgeInsets.fromLTRB(10, 5, 10, 7),
      decoration: BoxDecoration(color: const Color(0xEE0B1220), borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.warning.withValues(alpha: .6))),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(widget.wide ? '$text · do poziomu ${c.target}' : text,
            textAlign: TextAlign.center, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Colors.white)),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(value: c.progress(), minHeight: 6, color: AppColors.warning, backgroundColor: Colors.white12),
        ),
      ]),
    );
  }
}

/// M5: wariant grafiki budynku wg postępu poziomu (1 = niski, 2 = średni, 3 = wysoki).
int buildingTier(int level, int max) {
  final f = level / math.max(1, max);
  return f < .34 ? 1 : (f < .67 ? 2 : 3);
}

/// Grafika `assets/images/district/<id>_<tier>.png`; brak pliku → niższy wariant → [fallback] (bryła wektorowa).
class _BuildingArt extends StatelessWidget {
  const _BuildingArt({required this.id, required this.tier, required this.fallback});
  final String id;
  final int tier;
  final Widget fallback;
  @override
  Widget build(BuildContext context) {
    if (tier < 1) return fallback;
    return Image.asset(
      'assets/images/district/${id}_$tier.png',
      key: Key('bld-$id-$tier'),
      fit: BoxFit.contain,
      alignment: Alignment.bottomCenter,
      filterQuality: FilterQuality.medium,
      errorBuilder: (_, _, _) => _BuildingArt(id: id, tier: tier - 1, fallback: fallback),
    );
  }
}

// ───────────────────────────── teren wg etapu
class _GroundPainter extends CustomPainter {
  _GroundPainter(this.stage);
  final int stage;

  @override
  void paint(Canvas c, Size s) {
    final rnd = math.Random(42);
    // podłoże
    const grounds = {1: Color(0xFF3B4A2A), 2: Color(0xFF4A4A42), 3: Color(0xFF2A3346), 4: Color(0xFF1A2438)};
    c.drawRect(Offset.zero & s, Paint()..color = grounds[stage]!);

    if (stage == 1) {
      // trawa, kałuże błota, rozkopy
      for (var i = 0; i < 260; i++) {
        final p = Offset(rnd.nextDouble() * s.width, rnd.nextDouble() * s.height);
        c.drawLine(p, p + Offset(rnd.nextDouble() * 4 - 2, -6), Paint()..color = const Color(0xFF5E7A3A)..strokeWidth = 2);
      }
      for (var i = 0; i < 9; i++) {
        final p = Offset(rnd.nextDouble() * s.width, rnd.nextDouble() * s.height);
        c.drawOval(Rect.fromCenter(center: p, width: 60 + rnd.nextDouble() * 80, height: 26 + rnd.nextDouble() * 30), Paint()..color = const Color(0xFF5A4630));
      }
      // ścieżka gruntowa
      c.drawLine(const Offset(0, 290), Offset(s.width, 290), Paint()..color = const Color(0xFF6B5638)..strokeWidth = 34);
      return;
    }

    // drogi wewnętrzne: żwir (2) → asfalt (3) → aleja z pasami i latarniami (4)
    final roadColor = stage == 2 ? const Color(0xFF6E6A5E) : const Color(0xFF2B2F38);
    final road = Paint()..color = roadColor..strokeWidth = stage == 4 ? 46 : 36;
    c.drawLine(const Offset(0, 290), Offset(s.width, 290), road);
    c.drawLine(const Offset(370, 0), Offset(370, s.height), road);
    c.drawLine(const Offset(690, 290), Offset(690, s.height), road);
    if (stage >= 3) {
      final dash = Paint()..color = const Color(0xFFE8E2C8).withValues(alpha: .7)..strokeWidth = 2.5;
      for (double x = 10; x < s.width; x += 34) {
        c.drawLine(Offset(x, 290), Offset(x + 16, 290), dash);
      }
      for (double y = 10; y < s.height; y += 34) {
        c.drawLine(Offset(370, y), Offset(370, y + 16), dash);
      }
    }
    if (stage == 2) {
      // ogrodzenie placu budowy
      final fence = Paint()..color = const Color(0xFFF2B233)..strokeWidth = 3;
      c.drawRect(Rect.fromLTWH(30, 30, s.width - 60, s.height - 60), fence..style = PaintingStyle.stroke);
      for (double x = 30; x < s.width - 30; x += 40) {
        c.drawLine(Offset(x, 26), Offset(x, 36), fence);
        c.drawLine(Offset(x, s.height - 34), Offset(x, s.height - 24), fence);
      }
      // hałdy piasku
      for (final p in const [Offset(960, 260), Offset(330, 520), Offset(600, 530)]) {
        c.drawOval(Rect.fromCenter(center: p, width: 70, height: 30), Paint()..color = const Color(0xFFB59A62));
      }
    }
    if (stage >= 3) {
      // trawniki
      final lawn = Paint()..color = stage == 4 ? const Color(0xFF1F4A33) : const Color(0xFF26402F);
      for (final r in const [Rect.fromLTWH(20, 500, 320, 50), Rect.fromLTWH(610, 245, 360, 22), Rect.fromLTWH(940, 330, 50, 200)]) {
        c.drawRRect(RRect.fromRectAndRadius(r, const Radius.circular(10)), lawn);
      }
      // latarnie
      for (double x = 60; x < s.width; x += 140) {
        final p = Offset(x, 262);
        c.drawCircle(p, stage == 4 ? 26 : 18, Paint()..color = const Color(0xFFFFD27A).withValues(alpha: .14));
        c.drawCircle(p, 4, Paint()..color = const Color(0xFFFFE2A0));
      }
    }
    if (stage == 4) {
      // drzewa w alei + fontanna
      for (double x = 30; x < s.width; x += 70) {
        c.drawCircle(Offset(x, 322), 12, Paint()..color = const Color(0xFF2E7D4F));
      }
      const f = Offset(370, 290);
      c.drawCircle(f, 30, Paint()..color = const Color(0xFF8C93A6));
      c.drawCircle(f, 22, Paint()..color = const Color(0xFF3B82C4));
      c.drawCircle(f, 6, Paint()..color = const Color(0xFFBFE3FF));
    }
  }

  @override
  bool shouldRepaint(covariant _GroundPainter old) => old.stage != stage;
}

// ───────────────────────────── budynek jako obiekt na planie
class _BuildingObject extends StatelessWidget {
  const _BuildingObject({required this.b, this.cons, required this.stage, required this.anim, required this.ready, required this.full, required this.onTap});
  final Building b;
  final Construction? cons; // M5: trwa budowa tego budynku
  final int stage;
  final Animation<double> anim;
  final bool ready, full;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        key: Key('obj-${b.id}'),
        onTap: onTap,
        child: Stack(clipBehavior: Clip.none, children: [
          // M5: malowana grafika budynku wg wariantu poziomu; nie wybudowany → wytyczona parcela (wektor)
          // M5: nowy budynek w budowie → plac budowy (rusztowania, dźwig)
          if (b.level <= 0 && cons != null)
            Positioned(
              left: 6,
              right: 6,
              top: 4,
              bottom: 6,
              child: _Blend(
                stage: stage,
                child: Image.asset('assets/images/district/construction.png',
                    key: Key('bld-${b.id}-construction'), fit: BoxFit.contain, alignment: Alignment.bottomCenter, filterQuality: FilterQuality.medium),
              ),
            )
          else if (b.level <= 0)
            Positioned.fill(child: CustomPaint(painter: _BuildingPainter(b.id, b.level, b.max, stage)))
          else
            // budynek mieści się w obrysie parceli (mały margines), nie wchodzi na ulice
            Positioned(
              left: 6,
              right: 6,
              top: 4,
              bottom: 6,
              child: _Blend(
                stage: stage,
                scaffold: cons != null, // M5: rozbudowa → rusztowania na obecnym budynku
                child: _BuildingArt(id: b.id, tier: buildingTier(b.level, b.max), fallback: CustomPaint(painter: _BuildingPainter(b.id, b.level, b.max, stage))),
              ),
            ),
          // M5: pasek postępu budowy nad budynkiem
          if (cons != null)
            Positioned(left: 0, right: 0, top: -6, child: Center(child: ConstructionPill(c: cons!))),
          if (b.level > 0 && b.level >= b.max)
            const Positioned(left: 2, top: -20, child: Text('⭐', style: TextStyle(fontSize: 26, shadows: [Shadow(blurRadius: 6)]))),
          // podpis
          Positioned(
            left: -80,
            right: -80, // podpis może być szerszy od wąskiej parceli — bez łamania linii
            bottom: -30,
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                decoration: BoxDecoration(color: const Color(0xDD0B1220), borderRadius: BorderRadius.circular(8)),
                child: Text('${b.icon} ${b.name} · ${b.built ? 'Lvl ${b.level}' : (b.id == 'hall' ? '🔒' : 'plac')}',
                    style: TextStyle(fontSize: MediaQuery.sizeOf(context).width < 600 ? 22 : 15, fontWeight: FontWeight.w800, color: b.maxed ? AppColors.gold : Colors.white)),
              ),
            ),
          ),
          // 💸 dymek nad Kawiarnią / Klubem Nocnym, gdy skarbiec gotowy do odbioru
          if (ready)
            Positioned(
              left: 0,
              right: 0,
              top: -10,
              child: AnimatedBuilder(
                animation: anim,
                builder: (_, _) {
                  final v = anim.value;
                  return Opacity(
                    opacity: (v < .12 ? v / .12 : 1 - (v - .12) / .88 * .55).clamp(0.0, 1.0),
                    child: Transform.translate(
                      offset: Offset(math.sin(v * math.pi * 2) * 6, -50 * v),
                      child: Center(
                        child: Container(
                          key: Key('coin-${b.id}'),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: full ? AppColors.gold : AppColors.success,
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: const [BoxShadow(color: Color(0x88000000), blurRadius: 6)],
                          ),
                          child: Text(full ? '💸 PEŁNY!' : '💸', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Colors.black)),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
        ]),
      ),
    );
  }
}

/// Bryła budynku: nie wybudowany = wytyczona parcela; wysokość i detale rosną z poziomem i etapem dzielnicy.
class _BuildingPainter extends CustomPainter {
  _BuildingPainter(this.id, this.level, this.max, this.stage);
  final String id;
  final int level, max, stage;

  static const _colors = {
    'residence': Color(0xFF4AA8FF),
    'garage': Color(0xFF8A94A8),
    'cafe': Color(0xFFD08A4E),
    'nightclub': Color(0xFFB45CFF),
    'club': Color(0xFF3FBF7F),
    'hall': Color(0xFFE5B93B),
  };

  @override
  void paint(Canvas c, Size s) {
    final base = _colors[id]!;
    if (level <= 0) {
      // wytyczona parcela (przerywana ramka + palik)
      final p = Paint()
        ..color = Colors.white.withValues(alpha: .45)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3;
      final r = Rect.fromLTWH(10, 10, s.width - 20, s.height - 20);
      const step = 18.0;
      for (double x = r.left; x < r.right; x += step * 2) {
        c.drawLine(Offset(x, r.top), Offset(math.min(x + step, r.right), r.top), p);
        c.drawLine(Offset(x, r.bottom), Offset(math.min(x + step, r.right), r.bottom), p);
      }
      for (double y = r.top; y < r.bottom; y += step * 2) {
        c.drawLine(Offset(r.left, y), Offset(r.left, math.min(y + step, r.bottom)), p);
        c.drawLine(Offset(r.right, y), Offset(r.right, math.min(y + step, r.bottom)), p);
      }
      c.drawLine(r.center, r.center + const Offset(0, -26), Paint()..color = const Color(0xFFB08A50)..strokeWidth = 4);
      return;
    }
    final frac = (level / math.max(1, max)).clamp(0.0, 1.0);
    // etap 1–2: baraki / kontenery; etap 3: biura; etap 4: pełne bryły
    final hFrac = stage <= 2 ? .38 + .25 * frac : (stage == 3 ? .5 + .35 * frac : .62 + .38 * frac);
    final w = s.width * (stage <= 2 ? .72 : .86);
    final h = s.height * hFrac;
    final left = (s.width - w) / 2;
    final top = s.height - h - 6;
    final body = Rect.fromLTWH(left, top, w, h);
    // podjazd / fundament
    final foundation = stage == 2 ? const Color(0xFF8E8E86) : (stage >= 3 ? const Color(0xFF3A4152) : const Color(0xFF6B5638));
    c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(4, s.height - 16, s.width - 8, 14), const Radius.circular(4)), Paint()..color = foundation);
    // cień + bryła z „boczną ścianą” (pseudo-3D)
    c.drawRect(body.shift(const Offset(10, 8)), Paint()..color = const Color(0x55000000));
    final side = Path()
      ..moveTo(body.right, body.top)
      ..lineTo(body.right + 14, body.top - 10)
      ..lineTo(body.right + 14, body.bottom - 10)
      ..lineTo(body.right, body.bottom)
      ..close();
    c.drawPath(side, Paint()..color = Color.lerp(base, Colors.black, .45)!);
    final roof = Path()
      ..moveTo(body.left, body.top)
      ..lineTo(body.left + 14, body.top - 10)
      ..lineTo(body.right + 14, body.top - 10)
      ..lineTo(body.right, body.top)
      ..close();
    c.drawPath(roof, Paint()..color = Color.lerp(base, Colors.white, .25)!);
    c.drawRect(
      body,
      Paint()
        ..shader = LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [
          Color.lerp(base, Colors.white, stage == 4 ? .1 : 0)!,
          Color.lerp(base, Colors.black, stage <= 2 ? .45 : .3)!,
        ]).createShader(body),
    );
    // okna: siatka zależna od poziomu; od etapu 3 świecą
    final cols = (2 + (w / 40)).floor().clamp(2, 6);
    final rows = (1 + h / 34).floor().clamp(1, 6);
    final lit = stage >= 3;
    for (var r = 0; r < rows; r++) {
      for (var k = 0; k < cols; k++) {
        final ww = w / (cols * 1.6), wh = h / (rows * 2.2);
        final x = body.left + (k + .5) * w / cols - ww / 2;
        final y = body.top + (r + .4) * h / rows;
        final on = lit && ((r * 7 + k * 3 + level) % 4 != 0);
        c.drawRect(Rect.fromLTWH(x, y, ww, wh), Paint()..color = on ? const Color(0xFFFFE08A) : const Color(0xFF16233A));
      }
    }
    // akcenty specjalne
    if (id == 'hall' && stage == 4) {
      // posąg Sali Chwały na cokole
      final cx = body.center.dx, by = body.top - 14;
      c.drawRect(Rect.fromCenter(center: Offset(cx, by), width: 34, height: 12), Paint()..color = const Color(0xFFCFC6A8));
      c.drawCircle(Offset(cx, by - 30), 9, Paint()..color = AppColors.gold);
      c.drawRect(Rect.fromCenter(center: Offset(cx, by - 14), width: 14, height: 22), Paint()..color = AppColors.gold);
    }
    if (id == 'residence' && stage == 4) {
      // podjazd VIP: czerwony dywan
      c.drawRect(Rect.fromLTWH(body.center.dx - 12, body.bottom - 2, 24, 14), Paint()..color = const Color(0xFFC0392B));
    }
    if (stage == 2) {
      // dźwig budowlany przy obiekcie w rozbudowie
      if (level < max) {
        final p = Paint()..color = const Color(0xFFF2B233)..strokeWidth = 4;
        c.drawLine(Offset(body.right + 24, s.height - 10), Offset(body.right + 24, 6), p);
        c.drawLine(Offset(body.right + 24, 8), Offset(body.left + 10, 8), p);
      }
    }
    if (level >= max) {
      // gwiazdka maksymalnego poziomu
      c.drawCircle(Offset(body.left + 14, body.top + 14), 9, Paint()..color = AppColors.gold);
    }
  }

  @override
  bool shouldRepaint(covariant _BuildingPainter o) => o.level != level || o.stage != stage || o.max != max;
}
