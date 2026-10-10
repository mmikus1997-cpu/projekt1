import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../auth/auth_form.dart';
import 'map_board.dart';
import 'map_panel.dart';
import 'map_providers.dart';
import 'map_region.dart';
import 'map_widgets.dart';

/// UI v2 Etap 2 — „MAPA = ŚWIAT”: plansza na cały obszar, pasek asystenta u góry,
/// panel lokacji nad mapą (prawy panel ≥ 600 px, bottom sheet na telefonie). Mapa żyje w tle.
class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});
  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> with SingleTickerProviderStateMixin {
  Timer? _tick;
  int now = DateTime.now().millisecondsSinceEpoch;
  final _ctrl = TransformationController(); // trwały — pan/zoom nie resetuje się przy odświeżeniu
  Size? _fittedFor;
  // M3: dwupoziomowy zoom — null = mapa świata, id = widok okolicy tej dzielnicy
  int? _region;
  late final AnimationController _zoomAnim = AnimationController(vsync: this, duration: const Duration(milliseconds: 420));
  Animation<Matrix4>? _zoomTween;

  /// Klik dzielnicy: płynne przybliżenie planszy na dzielnicę, potem przejście (fade) do grafiki okolicy + panel.
  Future<void> _enterRegion(int id, MapData d, Size view) async {
    if (_zoomAnim.isAnimating) return;
    final p = d.layout.district(id).pos;
    final s0 = _ctrl.value.storage[0];
    final s1 = math.min(3.5, s0 * 2.6);
    final end = Matrix4.identity()
      ..translateByDouble(view.width / 2 - p.dx * s1, view.height / 2 - p.dy * s1, 0, 1)
      ..scaleByDouble(s1, s1, 1, 1);
    final back = _ctrl.value.clone();
    _zoomTween = Matrix4Tween(begin: back, end: end).animate(CurvedAnimation(parent: _zoomAnim, curve: Curves.easeInCubic));
    void tick() => _ctrl.value = _zoomTween!.value;
    _zoomAnim.addListener(tick);
    await _zoomAnim.forward(from: 0);
    _zoomAnim.removeListener(tick);
    if (!mounted) return;
    _ctrl.value = back; // po powrocie mapa świata wraca do poprzedniego kadru
    ref.read(mapSelectionProvider.notifier).state = MapSelection(MapSelKind.district, '$id');
    setState(() => _region = id);
  }

  void _leaveRegion() {
    ref.read(mapSelectionProvider.notifier).state = null;
    setState(() => _region = null);
  }

  @override
  void initState() {
    super.initState();
    _ctrl.addListener(_guardView);
    // odliczania (asystent, podróż) — co sekundę tylko lekkie paski, plansza ma własne RepaintBoundary
    _tick = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => now = DateTime.now().millisecondsSinceEpoch);
      // Popyt/lokacje muszą odświeżać się również bez wykonywania akcji gracza.
      if (timer.tick % 30 == 0) ref.invalidate(mapProvider);
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    _zoomAnim.dispose();
    _ctrl.dispose();
    super.dispose();
  }

  /// Dopasowanie planszy do okna (raz na rozmiar) — wyśrodkowane, z lekkim zbliżeniem na telefonie.
  // Twarda blokada: po każdej zmianie (kółko, gładzik, pinch, animacja) plansza zawsze pokrywa cały widok
  Size? _gView;
  MapLayout? _gLay;
  bool _guarding = false;
  void _guardView() {
    final v = _gView, l = _gLay;
    if (_guarding || v == null || l == null || v.isEmpty) return;
    final m = _ctrl.value;
    final s = m.storage[0];
    final t = m.getTranslation();
    final ns = math.max(s, coverScale(v, l));
    final tx = t.x.clamp(math.min(0.0, v.width - l.width * ns), 0.0).toDouble();
    final ty = t.y.clamp(math.min(0.0, v.height - l.height * ns), 0.0).toDouble();
    if ((ns - s).abs() < 1e-4 && (tx - t.x).abs() < .5 && (ty - t.y).abs() < .5) return;
    _guarding = true;
    _ctrl.value = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(ns, ns, 1, 1);
    _guarding = false;
  }

  void _fit(Size view, MapData d, {bool force = false}) {
    if (!force && _fittedFor == view) return;
    _fittedFor = view;
    final l = d.layout;
    final mobile = view.width < 600;
    final base = math.min(view.width / l.width, view.height / l.height);
    // M1: na telefonie plansza wypełnia cały ekran (bez pustych pasów nad/pod grafiką)
    final scale = mobile ? coverScale(view, l) * 1.05 : coverScale(view, l); // zawsze bez pustych pasów
    assert(base > 0);
    // na telefonie centrujemy na dzielnicy gracza
    final focus = mobile ? l.district(d.here).pos : Offset(l.width / 2, l.height / 2);
    var tx = view.width / 2 - focus.dx * scale;
    var ty = view.height / 2 - focus.dy * scale;
    // nie wyjeżdżamy poza krawędź grafiki, gdy plansza jest większa od okna
    if (l.width * scale >= view.width) tx = tx.clamp(view.width - l.width * scale, 0.0);
    if (l.height * scale >= view.height) ty = ty.clamp(view.height - l.height * scale, 0.0);
    _ctrl.value = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(scale, scale, 1, 1);
  }

  void _zoom(double f, Size view) {
    final c = Offset(view.width / 2, view.height / 2);
    final m = _ctrl.value.clone()
      ..translateByDouble(0, 0, 0, 1);
    final s = m.storage[0];
    final ns = (s * f).clamp(coverScale(view, ref.read(mapProvider).value!.layout), 3.5) / s;
    _ctrl.value = Matrix4.identity()
      ..translateByDouble(c.dx, c.dy, 0, 1)
      ..scaleByDouble(ns, ns, 1, 1)
      ..translateByDouble(-c.dx, -c.dy, 0, 1)
      ..multiply(m);
    // po oddaleniu przycinamy przesunięcie do krawędzi grafiki (bez ciemnych pasów)
    final l = ref.read(mapProvider).value!.layout;
    final v = _ctrl.value.clone();
    final sc = v.storage[0];
    final t = v.getTranslation();
    final tx = t.x.clamp(math.min(0.0, view.width - l.width * sc), 0.0).toDouble(), ty = t.y.clamp(math.min(0.0, view.height - l.height * sc), 0.0).toDouble();
    _ctrl.value = Matrix4.identity()
      ..translateByDouble(tx, ty, 0, 1)
      ..scaleByDouble(sc, sc, 1, 1);
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(mapProvider);
    return async.when(
      skipLoadingOnRefresh: true,
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            ErrorBanner('$e'),
            FilledButton(onPressed: () => ref.invalidate(mapProvider), child: const Text('Spróbuj ponownie')),
          ]),
        ),
      ),
      data: (d) => LayoutBuilder(builder: (context, c) {
        final view = Size(c.maxWidth, c.maxHeight);
        final relayout = _gView != view;
        _gView = view;
        _gLay = d.layout;
        if (relayout) WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _guardView(); });
        _fit(view, d);
        final mobile = c.maxWidth < 760; // M6: liczy się miejsce po odjęciu nawigacji, nie całe okno
        final sel = ref.watch(mapSelectionProvider);
        final panelW = c.maxWidth >= 1024 ? 420.0 : 380.0;
        final region = _region;
        // M3: zamknięcie panelu w widoku okolicy = powrót do mapy świata
        ref.listen(mapSelectionProvider, (prev, next) {
          if (next == null && prev != null && _region != null) setState(() => _region = null);
        });
        return Stack(children: [
          Positioned.fill(child: MapBoard(d: d, controller: _ctrl, viewport: view, onDistrict: (id) => _enterRegion(id, d, view))),
          // M3: widok okolicy nad planszą (fade + lekkie „dojechanie” kamery)
          Positioned.fill(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              transitionBuilder: (child, a) => FadeTransition(
                opacity: a,
                child: ScaleTransition(scale: Tween(begin: 1.06, end: 1.0).animate(a), child: child),
              ),
              child: region == null
                  ? const SizedBox.shrink(key: ValueKey('world'))
                  : MapRegionView(
                      key: ValueKey('region-$region'),
                      d: d,
                      district: region,
                      onBack: _leaveRegion,
                      rightInset: mobile ? 0 : panelW,
                      bottomInset: mobile ? c.maxHeight * 0.45 : 0,
                    ),
            ),
          ),
          // górny pasek asystenta + baner podróży (tylko na mapie świata)
          if (region == null)
          Positioned(
            left: mobile ? 8 : 16,
            right: mobile ? 8 : (sel != null ? panelW + 16 : 16),
            top: mobile ? 8 : 12,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              AssistantBar(d: d, now: now + d.clockOffsetMs, compact: mobile),
              if (d.travel != null) ...[const SizedBox(height: 8), TravelBanner(d: d, now: now)],
            ]),
          ),
          // sterowanie: zoom, wyśrodkowanie, dzień/noc (mapa świata)
          if (region == null)
          Positioned(
            left: mobile ? 8 : 16,
            bottom: mobile ? (sel != null ? c.maxHeight * 0.45 + 8 : 12) : 16,
            child: _MapControls(
              onIn: () => _zoom(1.25, view),
              onOut: () => _zoom(0.8, view),
              onCenter: () => _fit(view, d, force: true),
            ),
          ),
          // panel lokacji
          if (!mobile)
            AnimatedPositioned(
              duration: const Duration(milliseconds: 220),
              curve: Curves.easeOutCubic,
              top: 0,
              bottom: 0,
              right: sel == null ? -panelW - 20 : 0,
              width: panelW,
              child: Material(
                key: const Key('map-panel'),
                color: AppColors.surface,
                elevation: 12,
                child: Container(
                  decoration: const BoxDecoration(border: Border(left: BorderSide(color: AppColors.border))),
                  child: sel == null ? const SizedBox() : MapPanelContent(key: ValueKey(sel), sel: sel, d: d),
                ),
              ),
            )
          else if (sel != null)
            Positioned.fill(
              child: DraggableScrollableSheet(
                key: ValueKey('sheet-${sel.kind}-${sel.id}'),
                initialChildSize: 0.45,
                minChildSize: 0.2,
                maxChildSize: 0.92,
                snap: true,
                builder: (context, scroll) => Material(
                  key: const Key('map-panel'),
                  color: AppColors.surface,
                  elevation: 16,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
                  clipBehavior: Clip.antiAlias,
                  child: Column(children: [
                    // uchwyt do przeciągania
                    Container(
                      margin: const EdgeInsets.only(top: 8),
                      width: 44,
                      height: 5,
                      decoration: BoxDecoration(color: AppColors.border, borderRadius: BorderRadius.circular(3)),
                    ),
                    Expanded(child: MapPanelContent(sel: sel, d: d, scroll: scroll)),
                  ]),
                ),
              ),
            ),
        ]);
      }),
    );
  }
}

class _MapControls extends ConsumerWidget {
  const _MapControls({required this.onIn, required this.onOut, required this.onCenter});
  final VoidCallback onIn, onOut, onCenter;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(dayNightModeProvider);
    final (icon, tip, next) = switch (mode) {
      'auto' => ('🕒', 'Dzień/noc: wg czasu serwera', 'day'),
      'day' => ('☀️', 'Podgląd: dzień', 'night'),
      _ => ('🌙', 'Podgląd: noc', 'auto'),
    };
    Widget btn(Widget child, String tooltip, VoidCallback onTap, Key key) => Tooltip(
          message: tooltip,
          child: Material(
            color: AppColors.surface.withValues(alpha: .92),
            shape: const CircleBorder(side: BorderSide(color: AppColors.border)),
            child: InkWell(key: key, customBorder: const CircleBorder(), onTap: onTap, child: SizedBox(width: 40, height: 40, child: Center(child: child))),
          ),
        );
    return Column(mainAxisSize: MainAxisSize.min, children: [
      btn(const Icon(Icons.add_rounded, size: 20), 'Przybliż', onIn, const Key('map-zoom-in')),
      const SizedBox(height: 6),
      btn(const Icon(Icons.remove_rounded, size: 20), 'Oddal', onOut, const Key('map-zoom-out')),
      const SizedBox(height: 6),
      btn(const Icon(Icons.center_focus_strong_rounded, size: 20), 'Wyśrodkuj', onCenter, const Key('map-center')),
      const SizedBox(height: 6),
      btn(Text(icon, style: const TextStyle(fontSize: 17)), tip, () => ref.read(dayNightModeProvider.notifier).state = next, const Key('map-daynight')),
    ]);
  }
}
