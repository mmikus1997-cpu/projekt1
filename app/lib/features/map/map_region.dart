import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'map_board.dart';
import 'map_layout.dart';
import 'map_providers.dart';
import 'map_widgets.dart' show demandBadge, demandColor;

/// M3: konfiguracja widoku okolicy (map_data.json → art.regions["id"]).
/// rect = fragment planszy [x, y, w, h] w proporcjach 10:7, który pokazuje grafika regionu.
class MapRegionArt {
  MapRegionArt(this.asset, this.rect);
  final String asset;
  final Rect rect;

  static MapRegionArt? of(MapLayout l, int district) {
    final r = ((l.j['art'] as Map?)?['regions'] as Map?)?['$district'];
    if (r is! Map) return null;
    final q = r['rect'];
    if (q is! List || q.length != 4) return null;
    return MapRegionArt('${r['asset']}', Rect.fromLTWH((q[0] as num).toDouble(), (q[1] as num).toDouble(), (q[2] as num).toDouble(), (q[3] as num).toDouble()));
  }
}

/// Bliższy widok jednej dzielnicy: osobna malowana grafika, pinezki usług w tych samych współrzędnych planszy
/// (przeliczone na prostokąt regionu), panel danych nakłada MapScreen. [rightInset] = miejsce zajęte przez panel.
class MapRegionView extends ConsumerStatefulWidget {
  const MapRegionView({super.key, required this.d, required this.district, required this.onBack, this.rightInset = 0, this.bottomInset = 0});
  final MapData d;
  final int district;
  final VoidCallback onBack;
  final double rightInset, bottomInset;
  @override
  ConsumerState<MapRegionView> createState() => _MapRegionViewState();
}

class _MapRegionViewState extends ConsumerState<MapRegionView> {
  @override
  Widget build(BuildContext context) {
    final d = widget.d;
    final l = d.layout;
    final m = l.district(widget.district);
    final art = MapRegionArt.of(l, widget.district) ??
        MapRegionArt(l.artAsset ?? '', Rect.fromCenter(center: m.pos, width: 480, height: 336)); // fallback: wycinek mapy świata
    final sel = ref.watch(mapSelectionProvider);
    void select(MapSelection s) => ref.read(mapSelectionProvider.notifier).state = s;
    final slots = l.services.where((s) => s.district == widget.district).toList();

    return LayoutBuilder(builder: (context, c) {
      // Nieruchomy kadr: grafika wypełnia całą część ekranu niezasłoniętą panelem („cover”, bez ramki),
      // wycentrowana na dzielnicy i jej usługach. Bez przesuwania i zoomu.
      final vw = c.maxWidth - widget.rightInset, vh = c.maxHeight - widget.bottomInset;
      final s = math.max(vw / art.rect.width, vh / art.rect.height);
      final size = Size(art.rect.width * s, art.rect.height * s);
      final pts = [m.pos, for (final x in slots) x.pos];
      final cx = pts.map((p) => p.dx).reduce((a, b) => a + b) / pts.length, cy = pts.map((p) => p.dy).reduce((a, b) => a + b) / pts.length;
      final ox = ((cx - art.rect.left) * s - vw / 2).clamp(0.0, size.width - vw);
      final oy = ((cy - art.rect.top) * s - vh / 2 - 20).clamp(0.0, size.height - vh);
      // pozycja na ekranie; pinezki zawsze w kadrze (margines od krawędzi)
      Offset at(Offset board, {double mx = 90, double my = 40}) {
        final p = (board - art.rect.topLeft) * s - Offset(ox, oy);
        return Offset(p.dx.clamp(mx, math.max(mx, vw - mx)), p.dy.clamp(my + 56, math.max(my + 56, vh - my)));
      }

      final dp = at(m.pos, mx: 70, my: 50);
      return Stack(children: [
        // klik w tło (poza pinezkami, także obszar pod panelem) → powrót do mapy świata
        Positioned.fill(child: GestureDetector(key: const Key('region-bg'), behavior: HitTestBehavior.opaque, onTap: widget.onBack)),
        Positioned(
          left: 0,
          top: 0,
          width: vw,
          height: vh,
          child: ClipRect(
            child: Stack(clipBehavior: Clip.hardEdge, children: [
              Positioned(left: -ox, top: -oy, width: size.width, height: size.height, child: IgnorePointer(child: _RegionImage(art: art, layout: l))),
              // miękkie przyciemnienie krawędzi zamiast ramki — obraz „wtapia się” w UI
              const Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: RadialGradient(radius: 1.05, colors: [Color(0x00000000), Color(0x00000000), Color(0x660B1220)], stops: [0, .6, 1]),
                    ),
                  ),
                ),
              ),
              Positioned(
                left: dp.dx - 70,
                top: dp.dy - 40,
                width: 140,
                child: GestureDetector(
                  key: const Key('region-district'),
                  onTap: () => select(MapSelection(MapSelKind.district, '${m.id}')),
                  child: Column(children: [
                    Container(
                      width: 60,
                      height: 60,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.surface.withValues(alpha: .9),
                        border: Border.all(color: d.here == m.id ? AppColors.primary : AppColors.gold, width: 3),
                        boxShadow: const [BoxShadow(color: Color(0x88000000), blurRadius: 10, offset: Offset(0, 4))],
                      ),
                      child: Text(m.icon, style: const TextStyle(fontSize: 28)),
                    ),
                    const SizedBox(height: 4),
                    _chip(d.here == m.id ? '${m.name} · TU JESTEŚ' : m.name, d.here == m.id ? AppColors.primary : AppColors.textPrimary),
                  ]),
                ),
              ),
              for (final slot in slots)
                if (d.service(slot.id) case final sv?)
                  _RegionPin(
                    pos: at(slot.pos),
                    s: sv,
                    selected: sel == MapSelection(MapSelKind.service, slot.id),
                    onTap: () => select(MapSelection(MapSelKind.service, slot.id)),
                  ),
            ]),
          ),
        ),
        // pasek: powrót do mapy świata + nazwa okolicy
        Positioned(
          left: 12,
          top: 12,
          right: widget.rightInset + 12,
          child: Row(children: [
            Material(
              color: AppColors.surface.withValues(alpha: .94),
              borderRadius: BorderRadius.circular(22),
              child: InkWell(
                key: const Key('region-back'),
                borderRadius: BorderRadius.circular(22),
                onTap: widget.onBack,
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.arrow_back_rounded, size: 18),
                    SizedBox(width: 6),
                    Text('Mapa świata', style: TextStyle(fontWeight: FontWeight.w800)),
                  ]),
                ),
              ),
            ),
            const SizedBox(width: 10),
            Flexible(child: _chip('${m.icon} ${m.name} · ${slots.length} ${_uslugi(slots.length)}', AppColors.gold, big: true)),
          ]),
        ),
      ]);
    });
  }
}

Widget _chip(String t, Color c, {bool big = false}) => Container(
      padding: EdgeInsets.symmetric(horizontal: big ? 12 : 8, vertical: big ? 8 : 3),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: .92),
        borderRadius: BorderRadius.circular(big ? 20 : 8),
        boxShadow: const [BoxShadow(color: Color(0x55000000), blurRadius: 4, offset: Offset(0, 2))],
      ),
      child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
          style: TextStyle(fontSize: big ? 14 : 11, fontWeight: FontWeight.w900, color: c)),
    );

/// Grafika regionu; gdy pliku brak — wycinek mapy świata (ta sama ścieżka co tło planszy).
class _RegionImage extends StatelessWidget {
  const _RegionImage({required this.art, required this.layout});
  final MapRegionArt art;
  final MapLayout layout;
  @override
  Widget build(BuildContext context) {
    Widget world() {
      final a = layout.artAsset;
      if (a == null) return const ColoredBox(color: AppColors.surface);
      return LayoutBuilder(builder: (_, c) {
        final s = c.maxWidth / art.rect.width;
        return ClipRect(
          child: OverflowBox(
            alignment: Alignment.topLeft,
            maxWidth: double.infinity,
            maxHeight: double.infinity,
            child: Transform.translate(
              offset: -art.rect.topLeft * s,
              child: Image.asset(a, width: layout.width * s, height: layout.height * s, fit: BoxFit.fill),
            ),
          ),
        );
      });
    }

    return Image.asset(art.asset, key: const Key('region-art'), fit: BoxFit.fill, filterQuality: FilterQuality.medium, errorBuilder: (_, _, _) => world());
  }
}

class _RegionPin extends StatelessWidget {
  const _RegionPin({required this.pos, required this.s, required this.selected, required this.onTap});
  final Offset pos;
  final MapService s;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final pct = s.demandPct;
    final c = demandColor(pct);
    return Positioned(
      left: pos.dx - 85,
      top: pos.dy - 26,
      width: 170,
      child: Center(
        child: GestureDetector(
          key: Key('rpin-${s.id}'),
          onTap: onTap,
          child: AnimatedScale(
            scale: selected ? 1.08 : 1,
            duration: const Duration(milliseconds: 160),
            child: Container(
              padding: const EdgeInsets.fromLTRB(8, 6, 12, 6),
              decoration: BoxDecoration(
                color: AppColors.surface.withValues(alpha: .95),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: selected ? AppColors.gold : c.withValues(alpha: .8), width: selected ? 2.5 : 1.5),
                boxShadow: const [BoxShadow(color: Color(0x77000000), blurRadius: 8, offset: Offset(0, 3))],
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text(s.unlocked ? s.icon : '🔒', style: const TextStyle(fontSize: 22)),
                const SizedBox(width: 6),
                Flexible(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    Text(s.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, height: 1.15)),
                    Text('${demandBadge(pct)} $pct% · ${money(s.rateNow)}/h',
                        maxLines: 1, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: c, height: 1.2)),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// Polska odmiana: 1 usługa, 2–4 usługi, 5+ usług (12–14 → usług).
String _uslugi(int n) => n == 1 ? 'usługa' : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? 'usługi' : 'usług');
