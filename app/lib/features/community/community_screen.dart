import 'package:flutter/material.dart';

import '../../core/widgets/hub_tabs.dart';
import '../alliance/alliance_screen.dart';
import '../ranking/ranking_screen.dart';

/// Zakładka „Społeczność”: Mój Sojusz + Ranking Świata (scalone ekrany, bez zmian w logice).
class CommunityScreen extends StatelessWidget {
  const CommunityScreen({super.key, this.tab});
  final String? tab;
  static const ids = ['alliance', 'ranking'];

  @override
  Widget build(BuildContext context) => HubTabs(
        initial: hubIndex(ids, tab),
        tabs: const [
          ('alliance', '🤝 Mój Sojusz', AllianceScreen()),
          ('ranking', '🏆 Ranking Świata', RankingScreen()),
        ],
      );
}
