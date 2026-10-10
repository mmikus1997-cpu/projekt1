import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/i18n.dart';
import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/common.dart';
import '../../shared/models/models.dart';
import '../auth/auth_controller.dart';
import '../auth/auth_form.dart';
import 'world_providers.dart';

class WorldSelectScreen extends ConsumerWidget {
  const WorldSelectScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    final worlds = ref.watch(worldsProvider);
    final auth = ref.watch(authControllerProvider);
    return Scaffold(
      body: CityBackground(
        child: SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 8, 0),
              child: Row(children: [
                const Logo(size: 18),
                const Spacer(),
                const LanguageMenu(),
                IconButton(
                  tooltip: t.t('auth.logout'),
                  onPressed: () => ref.read(authControllerProvider.notifier).logout(),
                  icon: const Icon(Icons.logout_rounded),
                ),
              ]),
            ),
            Expanded(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 720),
                  child: ListView(padding: const EdgeInsets.all(20), children: [
                    Text(t.t('world.choose'), style: Theme.of(context).textTheme.headlineLarge),
                    if (auth.user != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4, bottom: 8),
                        child: Text('@${auth.user!.username}', style: const TextStyle(color: AppColors.textSecondary)),
                      ),
                    if (auth.guardianPending) ErrorBanner(t.t('auth.pending')),
                    const SizedBox(height: 12),
                    worlds.when(
                      loading: () => const Padding(
                          padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator())),
                      error: (e, _) => ErrorBanner('$e'),
                      data: (list) => Column(children: [
                        for (final w in list) Padding(padding: const EdgeInsets.only(bottom: 12), child: _WorldCard(w)),
                      ]),
                    ),
                  ]),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

class _WorldCard extends ConsumerWidget {
  const _WorldCard(this.w);
  final WorldInfo w;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = ref.watch(translationsProvider);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.public, color: AppColors.primary),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(w.name, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 2),
              Text(
                [
                  if (w.eraLabel.isNotEmpty) w.eraLabel,
                  if (w.kind == 'test') '${t.t('world.test')} ×${w.speed}',
                  if (w.hasCharacter) '👤 ${w.characterName}',
                ].join(' · '),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ]),
          ),
          const SizedBox(width: 12),
          if (w.hasCharacter)
            FilledButton(
              key: Key('world-enter-${w.id}'),
              style: FilledButton.styleFrom(minimumSize: const Size(96, 44)),
              onPressed: () => ref.read(worldIdProvider.notifier).select(w.id),
              child: Text(t.t('world.enter')),
            )
          else if (w.registrationOpen)
            OutlinedButton(
              key: Key('world-create-${w.id}'),
              style: OutlinedButton.styleFrom(minimumSize: const Size(96, 44)),
              onPressed: () => showDialog<void>(context: context, builder: (_) => _CreateCharacterDialog(w)),
              child: Text(t.t('world.create')),
            )
          else
            Text(t.t('world.closed'), style: const TextStyle(color: AppColors.textSecondary)),
        ]),
      ),
    );
  }
}

class _CreateCharacterDialog extends ConsumerStatefulWidget {
  const _CreateCharacterDialog(this.w);
  final WorldInfo w;
  @override
  ConsumerState<_CreateCharacterDialog> createState() => _CreateCharacterDialogState();
}

class _CreateCharacterDialogState extends ConsumerState<_CreateCharacterDialog> {
  final _nick = TextEditingController();
  bool _accept = false; // potwierdzenie zasad serwera testowego (wymagane dla światów test/experimental)
  bool get _isTest => const ['test', 'experimental'].contains(widget.w.kind);
  bool _busy = false;
  String? _error;

  Future<void> _create() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(apiClientProvider)
          .post('/api/worlds/${widget.w.id}/character', {'nickname': _nick.text.trim(), 'accept_test_reset': _accept});
      await ref.read(worldIdProvider.notifier).select(widget.w.id);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _nick.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = ref.watch(translationsProvider);
    return AlertDialog(
      backgroundColor: AppColors.surface,
      title: Text('${t.t('world.create')} · ${widget.w.name}'),
      content: SizedBox(
        width: 380,
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          if (_error != null) ErrorBanner(_error!),
          TextField(
            key: const Key('char-nick'),
            controller: _nick,
            decoration: InputDecoration(labelText: t.t('world.nickname')),
          ),
          if (_isTest) ...[
            const SizedBox(height: 12),
            CheckboxListTile(
              key: const Key('char-accept'),
              value: _accept,
              onChanged: (v) => setState(() => _accept = v ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(t.t('world.acceptTest')),
              subtitle: Text(t.t('world.acceptTestHint'), style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
            ),
          ],
          const SizedBox(height: 8),
          // klasa (taktyka) wybierana dopiero przy odblokowaniu PvP — backend: POST /class
          Row(children: [
            const Icon(Icons.sports_mma_rounded, size: 16, color: AppColors.textSecondary),
            const SizedBox(width: 8),
            Expanded(child: Text(t.t('world.classLater'), style: const TextStyle(fontSize: 12.5, color: AppColors.textSecondary))),
          ]),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: Text(t.t('common.back'))),
        FilledButton(
          key: const Key('char-submit'),
          style: FilledButton.styleFrom(minimumSize: const Size(120, 44)),
          onPressed: _busy || (_isTest && !_accept) ? null : _create,
          child: Text(t.t('world.create')),
        ),
      ],
    );
  }
}
