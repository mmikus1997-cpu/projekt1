import 'package:flutter/material.dart';

import '../../core/widgets/hub_tabs.dart';
import '../club/gear_screen.dart';
import '../club/shop_screen.dart';

/// Zakładka „Sklep & EQ”: Sklep z setami/kuponami + Ekwipunek z Warsztatem (crafting 3 w 1).
class ShopEqScreen extends StatelessWidget {
  const ShopEqScreen({super.key, this.tab});
  final String? tab;
  static const ids = ['shop', 'gear'];

  @override
  Widget build(BuildContext context) => HubTabs(
        initial: hubIndex(ids, tab),
        tabs: const [
          ('shop', '🛍️ Sklep', ShopScreen(embedded: true)),
          ('gear', '🎒 Ekwipunek i Warsztat', GearScreen(embedded: true)),
        ],
      );
}
