import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:socket_io_client/socket_io_client.dart' as io;

import '../config.dart';

/// Klient real-time. UWAGA: backend (Etap 1–8) nie wystawia jeszcze Socket.IO —
/// do tego czasu klient jest wyłączony, a ekrany odświeżają dane pollingiem.
/// Włączenie: `--dart-define=REALTIME=1`, gdy serwer dostanie endpoint /socket.io.
class SocketClient {
  static const enabled = bool.fromEnvironment('REALTIME');
  io.Socket? _socket;

  void connect(String token) {
    if (!enabled || _socket != null) return;
    _socket = io.io(
      AppConfig.apiBase,
      io.OptionBuilder().setTransports(['websocket']).setAuth({'token': token}).disableAutoConnect().build(),
    )..connect();
  }

  void on(String event, void Function(dynamic) handler) => _socket?.on(event, handler);

  void dispose() {
    _socket?.dispose();
    _socket = null;
  }
}

final socketClientProvider = Provider<SocketClient>((ref) {
  final s = SocketClient();
  ref.onDispose(s.dispose);
  return s;
});
