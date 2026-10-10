import 'dart:ui';

/// M6: trasa pojazdu wyłącznie po odcinkach dróg. Pinezka lokalu nie musi
/// leżeć na jezdni — auto kończy na najbliższym dojeździe, nie jedzie przez las.
/// Źródłem geometrii pozostaje map_data.json; ta funkcja nie zna współrzędnych mapy.
List<Offset> routeOnRoads(List<List<Offset>> lines, Offset start, Offset destination, {Set<int>? destinationLines}) {
  final segments = <(Offset, Offset, int)>[];
  for (var k = 0; k < lines.length; k++) {
    for (var i = 1; i < lines[k].length; i++) {
      if ((lines[k][i] - lines[k][i - 1]).distance > .001) segments.add((lines[k][i - 1], lines[k][i], k));
    }
  }
  if (segments.isEmpty) return const [];
  (Offset, int)? project(Offset p, Set<int>? allowed) {
    var best = double.infinity;
    (Offset, int)? result;
    for (var i = 0; i < segments.length; i++) {
      final (a, b, line) = segments[i];
      if (allowed != null && !allowed.contains(line)) continue;
      final v = b - a;
      final t = (((p - a).dx * v.dx + (p - a).dy * v.dy) / v.distanceSquared).clamp(0.0, 1.0);
      final q = a + v * t;
      final distance = (p - q).distanceSquared;
      if (distance < best) { best = distance; result = (q, i); }
    }
    return result;
  }
  final from = project(start, null), to = project(destination, destinationLines);
  if (from == null || to == null) return const [];
  final graph = <Offset, Map<Offset, double>>{};
  void link(Offset a, Offset b) {
    graph.putIfAbsent(a, () => {});
    graph.putIfAbsent(b, () => {});
    if (a == b) return;
    final length = (b - a).distance;
    graph[a]![b] = length;
    graph[b]![a] = length;
  }
  for (final (a, b, _) in segments) { link(a, b); }
  for (final p in [from, to]) {
    final (a, b, _) = segments[p.$2];
    link(p.$1, a); link(p.$1, b);
  }
  // Dwa punkty na tej samej ulicy: bez zbędnej jazdy do jej końca i zawracania.
  if (from.$2 == to.$2) link(from.$1, to.$1);
  final distances = <Offset, double>{from.$1: 0};
  final previous = <Offset, Offset>{};
  final visited = <Offset>{};
  while (true) {
    Offset? current;
    var best = double.infinity;
    for (final entry in distances.entries) {
      if (!visited.contains(entry.key) && entry.value < best) { current = entry.key; best = entry.value; }
    }
    if (current == null) return const []; // brak drogi: bez rysowania skrótu przez teren
    if (current == to.$1) break;
    visited.add(current);
    for (final edge in graph[current]!.entries) {
      final candidate = best + edge.value;
      if (candidate < (distances[edge.key] ?? double.infinity)) {
        distances[edge.key] = candidate;
        previous[edge.key] = current;
      }
    }
  }
  final result = <Offset>[to.$1];
  while (result.last != from.$1) { result.add(previous[result.last]!); }
  return result.reversed.toList();
}
