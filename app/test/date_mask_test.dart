import 'package:city_empire/features/auth/register_screen.dart';
import 'package:flutter_test/flutter_test.dart';

/// Symuluje wpisywanie znak po znaku przez maskę RRRR-MM-DD.
String typeChars(String chars) {
  final f = DateMaskFormatter();
  var v = TextEditingValue.empty;
  for (final ch in chars.split('')) {
    v = f.formatEditUpdate(v, TextEditingValue(text: v.text + ch));
  }
  return v.text;
}

void main() {
  test('po 4 cyfrach roku dopisuje myślnik', () => expect(typeChars('2000'), '2000-'));
  test('pełna data', () => expect(typeChars('20001015'), '2000-10-15'));
  test('max 10 znaków — nadmiar cyfr ignorowany', () => expect(typeChars('20001015999'), '2000-10-15'));
  test('litery i znaki ignorowane', () => expect(typeChars('2a0b0/0x1'), '2000-1'));
  test('kasowanie nie dokleja myślnika', () {
    final f = DateMaskFormatter();
    final r = f.formatEditUpdate(const TextEditingValue(text: '2000-'), const TextEditingValue(text: '2000'));
    expect(r.text, '2000');
  });
}
