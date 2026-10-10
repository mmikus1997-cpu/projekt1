import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/i18n.dart';
import 'auth_controller.dart';
import 'auth_form.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _busy = false, _obscure = true;
  String? _error;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authControllerProvider.notifier).login(_user.text, _pass.text).timeout(const Duration(seconds: 30), onTimeout: () => throw 'Serwer nie odpowiada (30 s). Spróbuj ponownie.');
      // router przekieruje po zmianie stanu auth
    } catch (e) {
      if (mounted) {
        setState(() => _error = '$e');
        // czerwony SnackBar z treścią błędu z backendu (detail) — obok banera w formularzu
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(
            content: Text('$e', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            backgroundColor: const Color(0xFFDC2626),
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 6),
          ));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _user.dispose();
    _pass.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = ref.watch(translationsProvider);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? t.t('auth.required') : null;
    return AuthFrame(title: t.t('auth.login'), children: [
      if (_error != null) ErrorBanner(_error!),
      Form(
        key: _form,
        child: AutofillGroup(
          child: Column(children: [
            TextFormField(
              key: const Key('login-username'),
              controller: _user,
              autofillHints: const [AutofillHints.username],
              decoration: InputDecoration(labelText: t.t('auth.username'), prefixIcon: const Icon(Icons.person_outline)),
              validator: req,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 14),
            TextFormField(
              key: const Key('login-password'),
              controller: _pass,
              obscureText: _obscure,
              autofillHints: const [AutofillHints.password],
              decoration: InputDecoration(
                labelText: t.t('auth.password'),
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
              ),
              validator: req,
              onFieldSubmitted: (_) => _submit(),
            ),
          ]),
        ),
      ),
      const SizedBox(height: 22),
      FilledButton(
        key: const Key('login-submit'),
        onPressed: _busy ? null : _submit,
        child: _busy
            ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
            : Text(t.t('auth.login')),
      ),
      const SizedBox(height: 8),
      TextButton(onPressed: () => context.go('/register'), child: Text(t.t('auth.noAccount'))),
    ]);
  }
}
