import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'map_layout.dart';

/// UI v2 Etap 5: tekstury PNG mapy z `assets/images/map/` (opis w map_data.json → "textures").
/// layer: "under" = pod drogami (teren), "over" = nad drogami (chmury, korony drzew).
/// Teraz to szare prostokąty zastępcze — docelowo grafiki AI w tych samych ścieżkach (bez zmian w kodzie).
class MapTexture {
  MapTexture(this.asset, this.layer, this.rect, this.opacity, this.maxPx);
  final String asset, layer;
  final Rect rect; // w jednostkach planszy
  final double opacity;
  final int maxPx; // limit szerokości po dekodowaniu (pamięć!)

  static List<MapTexture> of(MapLayout l) => [
        for (final t in (l.j['textures'] as List?) ?? const [])
          if (t is Map && t['enabled'] != false)
            MapTexture(
              '${t['asset']}',
              '${t['layer'] ?? 'under'}',
              switch (t['rect']) {
                [num x, num y, num w, num h] => Rect.fromLTWH(x.toDouble(), y.toDouble(), w.toDouble(), h.toDouble()),
                _ => Rect.fromLTWH(0, 0, l.width, l.height),
              },
              (t['opacity'] as num?)?.toDouble() ?? 1,
              (t['max_px'] as num?)?.toInt() ?? 2048,
            ),
      ];
}

/// Ładowanie w tle + downscale przy dekodowaniu (wielki PNG nie zajmie pełnej rozdzielczości w RAM).
/// autoDispose: wyjście z mapy zwalnia obraz (img.dispose()). Brak pliku → null (zostaje sama grafika wektorowa).
final mapTextureProvider = FutureProvider.autoDispose.family<ui.Image?, (String, int)>((ref, k) async {
  try {
    final data = await rootBundle.load(k.$1);
    // ImageDescriptor nie działa na Flutter Web → instantiateImageCodec z docelową szerokością (downscale przy dekodowaniu)
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List(), targetWidth: k.$2);
    final img = (await codec.getNextFrame()).image;
    codec.dispose();
    ref.onDispose(img.dispose);
    return img;
  } catch (e) {
    debugPrint('Tekstura mapy ${k.$1} niedostępna: $e');
    return null;
  }
});

class MapTextureLayer extends ConsumerWidget {
  const MapTextureLayer({super.key, required this.layout, required this.layer});
  final MapLayout layout;
  final String layer;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = MapTexture.of(layout).where((t) => t.layer == layer).toList();
    if (list.isEmpty) return const SizedBox.shrink();
    final imgs = [for (final t in list) ref.watch(mapTextureProvider((t.asset, t.maxPx))).valueOrNull];
    return IgnorePointer(
      child: RepaintBoundary(
        child: CustomPaint(key: Key('map-tex-$layer'), painter: _TexPainter(list, imgs), size: Size(layout.width, layout.height)),
      ),
    );
  }
}

class _TexPainter extends CustomPainter {
  _TexPainter(this.list, this.imgs);
  final List<MapTexture> list;
  final List<ui.Image?> imgs;

  @override
  void paint(Canvas c, Size size) {
    for (var i = 0; i < list.length; i++) {
      final img = imgs[i];
      if (img == null) continue;
      final src = Rect.fromLTWH(0, 0, img.width.toDouble(), img.height.toDouble());
      c.drawImageRect(img, src, list[i].rect, Paint()
        ..filterQuality = FilterQuality.low
        ..color = Color.fromRGBO(255, 255, 255, list[i].opacity));
    }
  }

  @override
  bool shouldRepaint(covariant _TexPainter old) => !listEquals(old.imgs, imgs);
}

bool listEquals<T>(List<T> a, List<T> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

/// M1: tło planszy z malowanej grafiki AI (map_data.json → art.world). Dopóki obraz się ładuje albo gdy go brak,
/// rysuje się dotychczasowy teren wektorowy — podmiana grafiki = nowy plik w tej samej ścieżce, bez zmian w kodzie.
class MapArtLayer extends ConsumerWidget {
  const MapArtLayer({super.key, required this.layout, required this.fallback});
  final MapLayout layout;
  final Widget fallback;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final a = layout.artAsset;
    if (a == null) return fallback;
    final img = ref.watch(mapTextureProvider((a, layout.artMaxPx))).valueOrNull;
    if (img == null) return fallback;
    return IgnorePointer(
      child: RepaintBoundary(
        child: CustomPaint(key: const Key('map-art'), painter: _ArtPainter(img), size: Size(layout.width, layout.height)),
      ),
    );
  }
}

class _ArtPainter extends CustomPainter {
  _ArtPainter(this.img);
  final ui.Image img;
  @override
  void paint(Canvas c, Size size) {
    final src = Rect.fromLTWH(0, 0, img.width.toDouble(), img.height.toDouble());
    c.drawImageRect(img, src, Offset.zero & size, Paint()..filterQuality = FilterQuality.medium);
    // delikatna winieta: brzegi mapy przechodzą w ciemniejszy krajobraz (dekoracja, bez punktów)
    final r = Offset.zero & size;
    c.drawRect(r, Paint()
      ..shader = RadialGradient(colors: const [Color(0x00000000), Color(0x00000000), Color(0x660A1322)], stops: const [0, .62, 1])
          .createShader(Rect.fromCenter(center: r.center, width: size.width * 1.15, height: size.height * 1.15)));
  }

  @override
  bool shouldRepaint(covariant _ArtPainter old) => old.img != img;
}
