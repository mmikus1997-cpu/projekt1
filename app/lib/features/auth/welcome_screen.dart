import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/config.dart';
import '../../core/i18n/i18n.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

class WelcomeScreen extends ConsumerWidget {
  const WelcomeScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return Scaffold(
      body: CityBackground(
        child: SafeArea(
          child: Column(children: [
            const Align(alignment: Alignment.topRight, child: Padding(padding: EdgeInsets.all(8), child: LanguageMenu())),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                      const Logo(size: 48),
                      const SizedBox(height: 16),
                      Text(t.t('app.tagline'),
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 16, color: AppColors.textSecondary, height: 1.4)),
                      const SizedBox(height: 56),
                      FilledButton.icon(
                        key: const Key('welcome-login'),
                        onPressed: () => context.go('/login'),
                        icon: const Icon(Icons.login_rounded),
                        label: Text(t.t('auth.login')),
                      ),
                      const SizedBox(height: 14),
                      OutlinedButton.icon(
                        key: const Key('welcome-register'),
                        onPressed: () => context.go('/register'),
                        icon: const Icon(Icons.person_add_alt_1_rounded),
                        label: Text(t.t('auth.register')),
                      ),
                    ]),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text('LIFE CITY · City Empire v${AppConfig.version} · GDD v3.1',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            ),
          ]),
        ),
      ),
    );
  }
}
