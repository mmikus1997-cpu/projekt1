import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';

/// Wspólna rama ekranów logowania/rejestracji: tło, karta, logo, przycisk wstecz.
class AuthFrame extends StatelessWidget {
  const AuthFrame({super.key, required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CityBackground(
        child: SafeArea(
          child: Stack(children: [
            Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(children: [
                    const Logo(size: 30),
                    const SizedBox(height: 28),
                    Card(
                      color: AppColors.surface.withValues(alpha: 0.92),
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                          Text(title, style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 20),
                          ...children,
                        ]),
                      ),
                    ),
                  ]),
                ),
              ),
            ),
            Positioned(
              left: 4,
              top: 4,
              child: IconButton(
                onPressed: () => context.go('/welcome'),
                icon: const Icon(Icons.arrow_back_rounded),
              ),
            ),
            const Positioned(right: 4, top: 4, child: LanguageMenu()),
          ]),
        ),
      ),
    );
  }
}

class ErrorBanner extends StatelessWidget {
  const ErrorBanner(this.message, {super.key});
  final String message;
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.danger.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.danger.withValues(alpha: 0.4)),
      ),
      child: Row(children: [
        const Icon(Icons.error_outline, color: AppColors.danger, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Text(message, style: const TextStyle(color: AppColors.danger))),
      ]),
    );
  }
}
