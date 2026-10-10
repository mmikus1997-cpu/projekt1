import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import 'auth_controller.dart';

/// Sprawdza zapisaną sesję; router sam przekieruje na /welcome albo /dashboard.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});
  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    // krótka pauza na pokaz logo, równolegle sprawdzenie sesji
    Future.wait([
      ref.read(authControllerProvider.notifier).restore(),
      Future<void>.delayed(const Duration(milliseconds: 900)),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: CityBackground(
        child: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Logo(size: 44),
            SizedBox(height: 40),
            SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 3, color: AppColors.primary)),
          ]),
        ),
      ),
    );
  }
}
