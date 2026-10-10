import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/alliance/alliance_providers.dart';
import '../../features/auth/auth_controller.dart';
import '../../features/dashboard/dashboard_providers.dart';
import '../../features/profile/profile_screen.dart';
import '../../features/welcome_back/welcome_back_dialog.dart';
import '../../features/world/world_providers.dart';
import '../../shared/models/models.dart';
import '../i18n/i18n.dart';
import '../theme/app_theme.dart';
import '../theme/breakpoints.dart';
import '../widgets/common.dart';
import '../widgets/hud_bar.dart';

class NavItem {
  const NavItem(this.path, this.icon, this.labelKey);
  final String path;
  final IconData icon;
  final String labelKey;
}

/// Etap 1 UI v2 (mapocentryczny): 6 zakładek, ta sama lista na każdej szerokości.
/// Profil / Battle Pass → awatar w HUD; Pulpit usunięty (start = Mapa + „Co się wydarzyło”).
const navItems = [
  NavItem('/district', Icons.apartment_rounded, 'nav.district'),
  NavItem('/map', Icons.map_rounded, 'nav.map'),
  NavItem('/crew', Icons.groups_rounded, 'nav.crew'),
  NavItem('/club', Icons.sports_mma_rounded, 'nav.club'),
  NavItem('/shopeq', Icons.storefront_rounded, 'nav.shopeq'),
  NavItem('/community', Icons.diversity_3_rounded, 'nav.community'),
];

/// Etap 4: czerwone plakietki z liczbą spraw do załatwienia (dane z /dashboard + /community dla podań).
/// Dzielnica: skarbce > 95% + auta zużyte w 100% · Ekipa: wypaleni / wszystkie potrzeby < 35% · Społeczność: podania (oficer) lub zaproszenia.
int navBadgeCount(String path, DashboardData? d, AllianceData? a) {
  switch (path) {
    case '/district':
      if (d == null) return 0;
      return d.vaultFills.values.where((f) => f > .95).length + d.brokenCars.length;
    case '/crew':
      return d?.warnNpcs.length ?? 0;
    case '/community':
      if (a == null) return 0;
      return a.inAlliance ? (a.isOfficer ? a.applications.length : 0) : a.invitations.length;
    default:
      return 0;
  }
}

/// Opis plakietki do podpowiedzi (tooltip).
String navBadgeHint(String path) => switch (path) {
      '/district' => 'Pełne skarbce / zepsute auta',
      '/crew' => 'NPC potrzebują odpoczynku',
      '/community' => 'Nowe podania / zaproszenia',
      _ => '',
    };

bool _isSelected(String location, String path) => location == path || location.startsWith('$path/');

// ───────────────────────────── historia nawigacji (strzałka Wstecz / Esc / gest systemowy)
class NavHistory extends Notifier<List<String>> {
  bool _skip = false;
  @override
  List<String> build() => const [];
  void visit(String loc) {
    if (_skip) {
      _skip = false;
      return;
    }
    if (state.isNotEmpty && state.last == loc) return;
    final next = [...state, loc];
    state = next.length > 30 ? next.sublist(next.length - 30) : next;
  }

  /// Zwraca lokację, do której należy wrócić (albo null, gdy nie ma dokąd).
  String? back() {
    if (state.length < 2) return null;
    state = state.sublist(0, state.length - 1);
    _skip = true;
    return state.last;
  }
}

final navHistoryProvider = NotifierProvider<NavHistory, List<String>>(NavHistory.new);

/// Profil + Battle Pass jako okno nad bieżącym ekranem (mapa dalej w tle).
Future<void> showProfileModal(BuildContext context) {
  final mobile = Breakpoints.isMobile(context);
  Widget body(BuildContext ctx) => Consumer(builder: (ctx, ref, _) {
        final t = ref.watch(translationsProvider);
        return Scaffold(
          backgroundColor: AppColors.background,
          appBar: AppBar(
            backgroundColor: AppColors.surface,
            title: const Text('Profil · Battle Pass', style: TextStyle(fontWeight: FontWeight.w800)),
            leading: IconButton(key: const Key('profile-close'), icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.of(ctx).pop()),
            actions: [
              const LanguageMenu(),
              IconButton(
                tooltip: t.t('auth.logout'),
                icon: const Icon(Icons.logout_rounded),
                onPressed: () async {
                  Navigator.of(ctx).pop();
                  ref.read(worldIdProvider.notifier).clear();
                  await ref.read(authControllerProvider.notifier).logout();
                },
              ),
            ],
          ),
          body: const ProfileScreen(),
        );
      });
  return showDialog(
    context: context,
    builder: (ctx) => mobile
        ? Dialog.fullscreen(child: body(ctx))
        : Dialog(
            clipBehavior: Clip.antiAlias,
            insetPadding: const EdgeInsets.all(32),
            child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 820), child: body(ctx)),
          ),
  );
}

/// Otacza ekrany po zalogowaniu. Telefon < 600: dolny pasek (chowany) · Tablet: wąski rail z ikonami · Desktop: zwijany sidebar.
class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key, required this.child});
  final Widget child;
  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  Timer? _poll;
  bool _bottomHidden = false;
  bool _sideCollapsed = false;

  @override
  void initState() {
    super.initState();
    // Brak WebSocketa w backendzie → polling stanu co 30 s.
    _poll = Timer.periodic(const Duration(seconds: 30), (_) => ref.invalidate(dashboardProvider));
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  void _back() {
    final to = ref.read(navHistoryProvider.notifier).back();
    final loc = GoRouterState.of(context).uri.path;
    if (to != null) {
      context.go(to);
    } else if (loc != '/map') {
      context.go('/map');
    }
  }

  @override
  Widget build(BuildContext context) {
    final uri = GoRouterState.of(context).uri;
    final location = uri.path;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(navHistoryProvider.notifier).visit(uri.toString());
    });
    final history = ref.watch(navHistoryProvider);
    final canBack = history.length > 1 || location != '/map';

    // „Co się wydarzyło” — raz na sesję dla danego świata, po pierwszych danych.
    ref.listen(dashboardProvider, (_, next) {
      final d = next.valueOrNull;
      final wid = ref.read(worldIdProvider);
      if (d == null || wid == null || ref.read(welcomeShownProvider) == wid) return;
      ref.read(welcomeShownProvider.notifier).state = wid;
      if (!d.hasNews) return; // Etap 4: tylko gdy są zarobki do odebrania lub zepsute auto
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) showWelcomeBack(context, d);
      });
    });

    final hud = HudBar(
      leading: canBack
          ? IconButton(key: const Key('nav-back'), tooltip: 'Wstecz (Esc)', onPressed: _back, icon: const Icon(Icons.arrow_back_rounded))
          : null,
      onAvatar: () => showProfileModal(context),
    );
    final content = Column(children: [hud, Expanded(child: widget.child)]);

    Widget scaffold;
    if (Breakpoints.isMobile(context)) {
      scaffold = Scaffold(
        body: content,
        bottomNavigationBar: _BottomBar(
          location: location,
          hidden: _bottomHidden,
          onToggle: () => setState(() => _bottomHidden = !_bottomHidden),
        ),
      );
    } else {
      final tablet = Breakpoints.isTablet(context);
      scaffold = Scaffold(
        body: Row(children: [
          _SideNav(
            location: location,
            collapsed: tablet || _sideCollapsed,
            canCollapse: !tablet,
            onToggle: () => setState(() => _sideCollapsed = !_sideCollapsed),
          ),
          Expanded(child: content),
        ]),
      );
    }

    return PopScope(
      canPop: !canBack,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: CallbackShortcuts(
        bindings: {const SingleActivator(LogicalKeyboardKey.escape): _back},
        child: Focus(autofocus: true, child: scaffold),
      ),
    );
  }
}

// ───────────────────────────── ikona z plakietką
class _NavIcon extends ConsumerWidget {
  const _NavIcon({required this.item, required this.color, this.size = 22});
  final NavItem item;
  final Color color;
  final double size;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ally = item.path == '/community' ? ref.watch(allianceProvider).valueOrNull : null;
    final n = navBadgeCount(item.path, ref.watch(dashboardProvider).valueOrNull, ally);
    final icon = Icon(item.icon, color: color, size: size);
    if (n <= 0) return icon;
    return Tooltip(
      message: navBadgeHint(item.path),
      child: Badge(
        key: Key('badge-${item.path.substring(1)}'),
        backgroundColor: AppColors.danger,
        textColor: Colors.white,
        offset: const Offset(8, -6),
        label: Text('$n', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900)),
        child: icon,
      ),
    );
  }
}

// ───────────────────────────── telefon: dolny pasek z uchwytem
class _BottomBar extends ConsumerWidget {
  const _BottomBar({required this.location, required this.hidden, required this.onToggle});
  final String location;
  final bool hidden;
  final VoidCallback onToggle;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return Container(
      decoration: const BoxDecoration(color: AppColors.surface, border: Border(top: BorderSide(color: AppColors.border))),
      child: SafeArea(
        top: false,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          InkWell(
            key: const Key('nav-handle'),
            onTap: onToggle,
            child: SizedBox(
              height: 18,
              width: double.infinity,
              child: Icon(hidden ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                  size: 18, color: AppColors.textSecondary),
            ),
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 180),
            child: hidden
                ? const SizedBox(width: double.infinity)
                : SizedBox(
                    height: 58,
                    child: Row(children: [
                      for (final n in navItems)
                        Expanded(child: _BottomItem(item: n, label: t.t(n.labelKey), selected: _isSelected(location, n.path))),
                    ]),
                  ),
          ),
        ]),
      ),
    );
  }
}

class _BottomItem extends StatelessWidget {
  const _BottomItem({required this.item, required this.label, required this.selected});
  final NavItem item;
  final String label;
  final bool selected;
  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.primary : AppColors.textSecondary;
    return InkWell(
      key: Key('nav-${item.path.substring(1)}'),
      onTap: () => context.go(item.path),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
          decoration: BoxDecoration(
            color: selected ? AppColors.primary.withValues(alpha: 0.18) : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
          ),
          child: _NavIcon(item: item, color: color),
        ),
        const SizedBox(height: 3),
        Text(label.split(' ').first,  // telefon: „Sklep”, „Społeczność” — bez nachodzenia
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 10, fontWeight: selected ? FontWeight.w800 : FontWeight.w600, color: color)),
      ]),
    );
  }
}

// ───────────────────────────── tablet (rail z ikonami) / desktop (ikony + podpisy, zwijany)
class _SideNav extends ConsumerWidget {
  const _SideNav({required this.location, required this.collapsed, required this.canCollapse, required this.onToggle});
  final String location;
  final bool collapsed, canCollapse;
  final VoidCallback onToggle;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: collapsed ? 76 : 232,
      decoration: const BoxDecoration(color: AppColors.surface, border: Border(right: BorderSide(color: AppColors.border))),
      child: SafeArea(
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(0, 20, 0, 20),
            child: collapsed
                ? const Icon(Icons.location_city_rounded, color: AppColors.primary, size: 30)
                : const Padding(padding: EdgeInsets.only(left: 20), child: _SideLogo()),
          ),
          for (final n in navItems)
            _SideItem(item: n, label: t.t(n.labelKey), selected: _isSelected(location, n.path), collapsed: collapsed),
          const Spacer(),
          if (canCollapse)
            IconButton(
              key: const Key('nav-collapse'),
              tooltip: collapsed ? 'Rozwiń menu' : 'Zwiń menu',
              onPressed: onToggle,
              icon: Icon(collapsed ? Icons.chevron_right_rounded : Icons.chevron_left_rounded),
            ),
          const SizedBox(height: 12),
        ]),
      ),
    );
  }
}

class _SideLogo extends StatelessWidget {
  const _SideLogo();
  @override
  Widget build(BuildContext context) {
    return const Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.location_city_rounded, color: AppColors.primary, size: 28),
      SizedBox(width: 10),
      Text.rich(TextSpan(children: [
        TextSpan(text: 'CITY '),
        TextSpan(text: 'EMPIRE', style: TextStyle(color: AppColors.primary)),
      ]), style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, letterSpacing: 1.2)),
    ]);
  }
}

class _SideItem extends StatelessWidget {
  const _SideItem({required this.item, required this.label, required this.selected, required this.collapsed});
  final NavItem item;
  final String label;
  final bool selected, collapsed;
  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.primary : AppColors.textSecondary;
    final tile = Material(
      color: selected ? AppColors.primary.withValues(alpha: 0.14) : Colors.transparent,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        key: Key('nav-${item.path.substring(1)}'),
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.go(item.path),
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : 14, vertical: 12),
          child: collapsed
              ? Center(child: _NavIcon(item: item, color: color))
              : Row(children: [
                  _NavIcon(item: item, color: color, size: 20),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(label,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                          color: selected ? AppColors.textPrimary : AppColors.textSecondary,
                        )),
                  ),
                ]),
        ),
      ),
    );
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: collapsed ? 10 : 12, vertical: 2),
      child: collapsed ? Tooltip(message: label, child: tile) : tile,
    );
  }
}
