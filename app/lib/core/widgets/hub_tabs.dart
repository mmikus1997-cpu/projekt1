import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Etap 1 UI v2: wspólny hub z pod-zakładkami (Społeczność, Sklep & EQ).
/// Zakładka startowa z parametru `?tab=` — linki z innych ekranów mogą wskazać konkretną.
class HubTabs extends StatelessWidget {
  const HubTabs({super.key, required this.tabs, this.initial = 0});
  final List<(String id, String label, Widget child)> tabs;
  final int initial;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: tabs.length,
      initialIndex: initial.clamp(0, tabs.length - 1),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Material(
          color: AppColors.surface,
          child: TabBar(
            labelColor: AppColors.primary,
            indicatorColor: AppColors.primary,
            unselectedLabelColor: AppColors.textSecondary,
            labelStyle: const TextStyle(fontWeight: FontWeight.w800),
            tabs: [for (final (id, label, _) in tabs) Tab(key: Key('hub-$id'), text: label)],
          ),
        ),
        Expanded(
          child: TabBarView(
            physics: const NeverScrollableScrollPhysics(), // przesuwanie zostaje dla list w środku
            children: [for (final (_, _, child) in tabs) child],
          ),
        ),
      ]),
    );
  }
}

int hubIndex(List<String> ids, String? tab) {
  final i = tab == null ? 0 : ids.indexOf(tab);
  return i < 0 ? 0 : i;
}
