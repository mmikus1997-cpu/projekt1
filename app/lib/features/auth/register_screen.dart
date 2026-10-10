import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/i18n.dart';
import '../../core/theme/app_theme.dart';
import 'auth_controller.dart';
import 'auth_form.dart';

/// Rejestracja z bramką wiekową (Etap 1.8): <12 lat backend odrzuca (422),
/// <16 lat wymaga e-maila opiekuna (zgoda rodzicielska, RODO).
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});
  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _user = TextEditingController();
  final _pass = TextEditingController();
  final _birth = TextEditingController();
  final _guardian = TextEditingController();
  bool _consent = false, _busy = false;
  String? _error;

  int? get _age {
    final d = DateTime.tryParse(_birth.text.trim());
    if (d == null || _birth.text.trim().length != 10) return null;
    final now = DateTime.now();
    var a = now.year - d.year;
    if (now.month < d.month || (now.month == d.month && now.day < d.day)) a--;
    return a;
  }

  bool get _minor => (_age ?? 99) < 16;

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authControllerProvider.notifier).register(
            username: _user.text,
            password: _pass.text,
            birthDate: _birth.text,
            consent: _consent,
            guardianEmail: _minor ? _guardian.text : null,
          ).timeout(const Duration(seconds: 30), onTimeout: () => throw 'Serwer nie odpowiada (30 s). Spróbuj ponownie.');
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
    for (final c in [_user, _pass, _birth, _guardian]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = ref.watch(translationsProvider);
    String? req(String? v) => (v == null || v.trim().isEmpty) ? t.t('auth.required') : null;
    return AuthFrame(title: t.t('auth.register'), children: [
      if (_error != null) ErrorBanner(_error!),
      Form(
        key: _form,
        child: Column(children: [
          TextFormField(
            key: const Key('reg-username'),
            controller: _user,
            decoration: InputDecoration(labelText: t.t('auth.username'), prefixIcon: const Icon(Icons.person_outline)),
            validator: req,
          ),
          const SizedBox(height: 14),
          TextFormField(
            key: const Key('reg-password'),
            controller: _pass,
            obscureText: true,
            decoration: InputDecoration(labelText: t.t('auth.password'), prefixIcon: const Icon(Icons.lock_outline)),
            validator: req,
          ),
          const SizedBox(height: 14),
          TextFormField(
            key: const Key('reg-birth'),
            controller: _birth,
            keyboardType: TextInputType.datetime,
            // maska RRRR-MM-DD: tylko cyfry, myślniki wstawiane automatycznie, max 10 znaków
            inputFormatters: [DateMaskFormatter()],
            decoration: InputDecoration(
              labelText: t.t('auth.birthDate'),
              helperText: t.t('auth.birthOptional'),
              prefixIcon: const Icon(Icons.cake_outlined),
              // wybór daty z kalendarza zamiast ręcznego wpisywania formatu
              suffixIcon: IconButton(
                tooltip: t.t('auth.pickDate'),
                icon: const Icon(Icons.calendar_month_rounded),
                onPressed: () async {
                  final now = DateTime.now();
                  final d = await showDatePicker(
                    context: context,
                    initialDate: DateTime.tryParse(_birth.text.trim()) ?? DateTime(now.year - 16, 1, 1),
                    firstDate: DateTime(1920),
                    lastDate: now,
                    initialDatePickerMode: DatePickerMode.year,
                  );
                  if (d != null) {
                    _birth.text = '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
                    setState(() {});
                  }
                },
              ),
            ),
            // pole opcjonalne (backend: birth_date opcjonalne); walidujemy tylko, gdy coś wpisano
            validator: (v) => (v ?? '').trim().isEmpty || _age != null ? null : t.t('auth.birthDate'),
            onChanged: (_) => setState(() {}),
          ),
          if (_minor && _age != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.gold.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.gold.withValues(alpha: 0.4)),
              ),
              child: Text(t.t('auth.guardianInfo'), style: const TextStyle(color: AppColors.gold)),
            ),
            const SizedBox(height: 14),
            TextFormField(
              key: const Key('reg-guardian'),
              controller: _guardian,
              keyboardType: TextInputType.emailAddress,
              decoration: InputDecoration(labelText: t.t('auth.guardianEmail'), prefixIcon: const Icon(Icons.mail_outline)),
              validator: req,
            ),
          ],
          const SizedBox(height: 10),
          CheckboxListTile(
            key: const Key('reg-consent'),
            value: _consent,
            onChanged: (v) => setState(() => _consent = v ?? false),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            title: Text(t.t('auth.consent'), style: const TextStyle(fontSize: 14)),
          ),
        ]),
      ),
      const SizedBox(height: 14),
      FilledButton(
        key: const Key('reg-submit'),
        onPressed: _busy || !_consent ? null : _submit,
        child: _busy
            ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
            : Text(t.t('auth.register')),
      ),
      const SizedBox(height: 8),
      TextButton(onPressed: () => context.go('/login'), child: Text(t.t('auth.haveAccount'))),
    ]);
  }
}


/// Maska daty RRRR-MM-DD: z samych cyfr buduje tekst z myślnikami (po 4. i 6. cyfrze), max 8 cyfr.
class DateMaskFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(TextEditingValue oldValue, TextEditingValue newValue) {
    var d = newValue.text.replaceAll(RegExp(r'\D'), '');
    if (d.length > 8) d = d.substring(0, 8);
    final b = StringBuffer();
    for (var i = 0; i < d.length; i++) {
      b.write(d[i]);
      if ((i == 3 || i == 5) && i < d.length - 1) b.write('-');
    }
    // myślnik od razu po pełnym roku / miesiącu, gdy użytkownik dopisuje (nie przy kasowaniu)
    final adding = newValue.text.length > oldValue.text.length;
    if (adding && (d.length == 4 || d.length == 6)) b.write('-');
    final t = b.toString();
    return TextEditingValue(text: t, selection: TextSelection.collapsed(offset: t.length));
  }
}
