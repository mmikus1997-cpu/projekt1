import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/auth_controller.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/register_screen.dart';
import '../../features/auth/splash_screen.dart';
import '../../features/auth/welcome_screen.dart';
import '../../features/club/club_screen.dart';
import '../../features/community/community_screen.dart';
import '../../features/shopeq/shop_eq_screen.dart';
import '../../features/crew/crew_screen.dart';
import '../../features/district/district_screen.dart';
import '../../features/map/map_screen.dart';
import '../../features/world/world_providers.dart';
import '../../features/world/world_select_screen.dart';
import '../widgets/common.dart';
import 'app_shell.dart';

/// Odświeża redirecty go_router przy zmianie auth lub wybranego świata.
class _RouterRefresh extends ChangeNotifier {
  _RouterRefresh(Ref ref) {
    ref.listen(authControllerProvider, (_, _) => notifyListeners());
    ref.listen(worldIdProvider, (_, _) => notifyListeners());
  }
}

const _public = {'/welcome', '/login', '/register'};

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: _RouterRefresh(ref),
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider).status;
      final world = ref.read(worldIdProvider);
      final loc = state.matchedLocation;
      if (auth == AuthStatus.unknown) return loc == '/' ? null : '/';
      if (auth == AuthStatus.loggedOut) return _public.contains(loc) ? null : '/welcome';
      // zalogowany
      if (world == null) return loc == '/worlds' ? null : '/worlds';
      if (loc == '/' || _public.contains(loc) || loc == '/worlds') return '/map';  // Etap 1 UI v2: start = Mapa (+ „Co się wydarzyło”)
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, _) => const SplashScreen()),
      GoRoute(path: '/welcome', builder: (_, _) => const WelcomeScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, _) => const RegisterScreen()),
      GoRoute(path: '/worlds', builder: (_, _) => const WorldSelectScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          // Zgodność wstecz: stare adresy → nowe zakładki
          GoRoute(path: '/dashboard', redirect: (_, _) => '/map'),
          GoRoute(path: '/alliance', redirect: (_, _) => '/community?tab=alliance'),
          GoRoute(path: '/ranking', redirect: (_, _) => '/community?tab=ranking'),
          GoRoute(path: '/shop', redirect: (_, _) => '/shopeq?tab=shop'),
          GoRoute(path: '/profile', redirect: (_, _) => '/map'),
          GoRoute(
            path: '/district',
            pageBuilder: (_, _) => const NoTransitionPage(child: DistrictScreen()),
            routes: [
              GoRoute(
                path: ':id',
                builder: (_, s) => PlaceholderScreen(titleKey: 'nav.district', icon: Icons.home_work_rounded),
              ),
            ],
          ),
          GoRoute(path: '/map', pageBuilder: (_, _) => const NoTransitionPage(child: MapScreen())),
          GoRoute(path: '/crew', pageBuilder: (_, _) => const NoTransitionPage(child: CrewScreen())),
          GoRoute(
            path: '/club',
            // UI v2 Etap 3: z Dzielnicy (extra: 'enter') — animowane „wejście do budynku” (fade + zoom).
            pageBuilder: (_, s) => s.extra == 'enter'
                ? CustomTransitionPage(
                    key: s.pageKey,
                    child: const ClubHouseScreen(),
                    transitionDuration: const Duration(milliseconds: 520),
                    transitionsBuilder: (_, a, _, child) {
                      final c = CurvedAnimation(parent: a, curve: Curves.easeOutCubic);
                      return FadeTransition(
                        opacity: c,
                        child: ScaleTransition(scale: Tween(begin: 1.12, end: 1.0).animate(c), child: child),
                      );
                    },
                  )
                : const NoTransitionPage(child: ClubHouseScreen()),
            routes: [
              GoRoute(path: 'fight', builder: (_, _) => const PlaceholderScreen(titleKey: 'nav.club', icon: Icons.sports_kabaddi_rounded)),
              GoRoute(path: 'gear', redirect: (_, _) => '/shopeq?tab=gear'),
            ],
          ),
          GoRoute(
            path: '/shopeq',
            pageBuilder: (_, s) => NoTransitionPage(
              key: ValueKey('shopeq-${s.uri.queryParameters['tab']}'),
              child: ShopEqScreen(tab: s.uri.queryParameters['tab']),
            ),
          ),
          GoRoute(
            path: '/community',
            pageBuilder: (_, s) => NoTransitionPage(
              key: ValueKey('community-${s.uri.queryParameters['tab']}'),
              child: CommunityScreen(tab: s.uri.queryParameters['tab']),
            ),
          ),
        ],
      ),
    ],
  );
});
