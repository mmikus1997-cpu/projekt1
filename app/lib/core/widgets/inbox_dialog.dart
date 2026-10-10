import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/dashboard/dashboard_providers.dart';
import '../../features/world/world_providers.dart';
import '../../shared/models/models.dart';
import '../network/api_client.dart';
import '../theme/app_theme.dart';

/// Dwa kanały w nagłówku — teraz na prawdziwych danych z backendu:
/// ✉️ Wiadomości: raporty walk (pvp_*), czat prywatny (/dm), sojusz (org.*, territory.*).
/// 🔔 Powiadomienia: Ekipa (npc.*), Budynki (stan skarbców/aut na żywo), Postać (season.*, inne), Miasto (city.*).
/// Zdarzenia pochodzą z tabeli game_events (GET /community → events, ostatnie 30); otwarcie okna oznacza je jako przeczytane.
enum InboxKind { messages, system }

enum InboxCat { fights, chat, alliance, crew, buildings, character, city }

InboxCat catOf(String kind) {
  if (kind.startsWith('npc.')) return InboxCat.crew;
  if (kind.startsWith('pvp')) return InboxCat.fights;
  if (kind.startsWith('org.') || kind.startsWith('territory.')) return InboxCat.alliance;
  if (kind.startsWith('city.')) return InboxCat.city;
  return InboxCat.character;
}

bool isMailCat(InboxCat c) => c == InboxCat.fights || c == InboxCat.chat || c == InboxCat.alliance;

class InboxEvent {
  InboxEvent(Map<String, dynamic> m)
      : id = (m['id'] as num?)?.toInt() ?? 0,
        kind = '${m['kind'] ?? ''}',
        payload = ((m['payload'] as Map?) ?? const {}).cast<String, dynamic>(),
        at = (m['created_at'] as num?)?.toInt() ?? 0,
        read = m['read'] == true;
  final int id, at;
  final String kind;
  final Map<String, dynamic> payload;
  final bool read;
  InboxCat get cat => catOf(kind);

  /// Czytelny tekst zdarzenia (backend często podaje gotowe `text`).
  String get text {
    final p = payload;
    if (p['text'] is String && (p['text'] as String).isNotEmpty) return p['text'] as String;
    String n(Object? v) => v is num ? (v == v.roundToDouble() ? '${v.round()}' : v.toStringAsFixed(1)) : '$v';
    return switch (kind) {
      'pvp_attacked' => '${p['attacker'] ?? 'Ktoś'} zaatakował Cię — ${p['result'] == 'win' ? 'wygrana' : (p['result'] == 'draw' ? 'remis' : 'porażka')}'
          '${p['change'] is num ? ' (Elo ${(p['change'] as num) >= 0 ? '+' : ''}${n(p['change'])})' : ''}',
      'org.invite' => 'Zaproszenie do sojuszu ${p['tag'] ?? p['name'] ?? ''}',
      'org.accepted' => 'Przyjęto Cię do sojuszu ${p['tag'] ?? p['name'] ?? ''}',
      'org.role' => 'Nowa rola w sojuszu: ${p['role'] ?? ''}',
      'territory.gained' => 'Sojusz przejął dzielnicę ${p['district'] ?? ''}',
      'territory.lost' => 'Sojusz stracił dzielnicę ${p['district'] ?? ''}${p['by'] != null ? ' na rzecz [${p['by']}]' : ''}',
      'city.event_created' => 'Nowe wydarzenie miasta: ${p['name'] ?? ''}',
      'city.event_done' => 'Wydarzenie zakończone sukcesem: ${p['name'] ?? ''} — tytuł Pioniera!',
      'city.event_missed' => 'Wydarzenie nieudane: ${p['name'] ?? ''}',
      'city.event_cancelled' => 'Wydarzenie odwołane: ${p['name'] ?? ''}',
      'season.end' => 'Koniec sezonu${p['season'] != null ? ' ${p['season']}' : ''}',
      'season.title' => 'Nowy tytuł sezonu: ${p['label'] ?? p['title'] ?? ''}',
      'season.reward' => 'Nagroda sezonowa: ${p['label'] ?? p['reward'] ?? ''}',
      _ => kind,
    };
  }

  String get icon => switch (cat) {
        InboxCat.fights => '⚔️',
        InboxCat.alliance => '🛡️',
        InboxCat.crew => kind == 'npc.shift_done' ? '💵' : '👥',
        InboxCat.city => '🏙️',
        _ => '🏅',
      };
}

class DmThread {
  DmThread(Map<String, dynamic> m)
      : nickname = '${m['nickname'] ?? ''}',
        last = '${m['last'] ?? ''}',
        at = (m['at'] as num?)?.toInt() ?? 0,
        unread = (m['unread'] as num?)?.toInt() ?? 0,
        mine = m['mine'] == true;
  final String nickname, last;
  final int at, unread;
  final bool mine;
}

class InboxData {
  InboxData(this.events, this.threads);
  final List<InboxEvent> events;
  final List<DmThread> threads;
  int unreadOf(bool mail) => events.where((e) => !e.read && isMailCat(e.cat) == mail).length;
}

final inboxProvider = FutureProvider.autoDispose<InboxData>((ref) async {
  final wid = ref.watch(worldIdProvider);
  if (wid == null) return InboxData(const [], const []);
  final api = ref.watch(apiClientProvider);
  final res = await Future.wait([
    api.get('/api/worlds/$wid/community').catchError((_) => <String, dynamic>{}),
    api.get('/api/worlds/$wid/dm').catchError((_) => <String, dynamic>{}),
  ]);
  return InboxData(
    [for (final e in (res[0]['events'] as List?) ?? const []) if (e is Map) InboxEvent(e.cast<String, dynamic>())],
    [for (final t in (res[1]['threads'] as List?) ?? const []) if (t is Map) DmThread(t.cast<String, dynamic>())],
  );
});

class _Tab {
  const _Tab(this.cat, this.label, this.icon, this.empty);
  final InboxCat cat;
  final String label;
  final IconData icon;
  final String empty;
}

const _tabs = {
  InboxKind.messages: [
    _Tab(InboxCat.fights, 'Raporty walk', Icons.sports_mma_rounded, 'Brak raportów z pojedynków PvP.'),
    _Tab(InboxCat.chat, 'Czat', Icons.chat_bubble_outline_rounded, 'Brak wiadomości prywatnych.'),
    _Tab(InboxCat.alliance, 'Sojusz', Icons.shield_outlined, 'Brak wiadomości sojuszu.'),
  ],
  InboxKind.system: [
    _Tab(InboxCat.crew, 'Ekipa', Icons.groups_rounded, 'Brak nowych zdarzeń Ekipy.'),
    _Tab(InboxCat.buildings, 'Budynki', Icons.storefront_rounded, 'Skarbce i auta w porządku.'),
    _Tab(InboxCat.character, 'Postać', Icons.military_tech_rounded, 'Brak nowych zdarzeń postaci.'),
    _Tab(InboxCat.city, 'Miasto', Icons.location_city_rounded, 'Brak wydarzeń miasta.'),
  ],
};

Future<void> showInbox(BuildContext context, InboxKind kind) => showDialog(
      context: context,
      builder: (_) => _InboxDialog(kind: kind),
    );

class _InboxDialog extends ConsumerStatefulWidget {
  const _InboxDialog({required this.kind});
  final InboxKind kind;
  @override
  ConsumerState<_InboxDialog> createState() => _InboxDialogState();
}

class _InboxDialogState extends ConsumerState<_InboxDialog> {
  bool _marked = false;

  /// Po wyświetleniu oznaczamy nieprzeczytane zdarzenia tego kanału jako przeczytane (licznik w nagłówku spada).
  Future<void> _markRead(InboxData d) async {
    if (_marked) return;
    _marked = true;
    final mail = widget.kind == InboxKind.messages;
    final ids = [for (final e in d.events) if (!e.read && isMailCat(e.cat) == mail) e.id];
    if (ids.isEmpty) return;
    final wid = ref.read(worldIdProvider);
    try {
      await ref.read(apiClientProvider).post('/api/worlds/$wid/events/read', {'ids': ids, 'all': false});
      // od razu zerujemy licznik w nagłówku (lista w oknie zostaje do zamknięcia — wyróżnienie „nowe” widać)
      if (mounted) {
        _keep = ref.read(inboxProvider).valueOrNull;
        ref.invalidate(dashboardProvider);
      }
    } catch (_) {}
  }

  InboxData? _keep;

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs[widget.kind]!;
    final isMail = widget.kind == InboxKind.messages;
    final live = ref.watch(inboxProvider);
    // po oznaczeniu jako przeczytane pokazujemy dalej migawkę z wyróżnieniem nowych (bez mrugania listy)
    final inbox = _keep != null ? AsyncValue.data(_keep!) : live;
    final dash = ref.watch(dashboardProvider).valueOrNull;
    final data = inbox.valueOrNull;
    if (data != null) WidgetsBinding.instance.addPostFrameCallback((_) => _markRead(data));
    int count(InboxCat c) => switch (c) {
          InboxCat.chat => data?.threads.fold<int>(0, (a, t) => a + t.unread) ?? 0,
          InboxCat.buildings => _buildingAlerts(dash).length,
          _ => data?.events.where((e) => e.cat == c && !e.read).length ?? 0,
        };
    return Dialog(
      backgroundColor: AppColors.surface,
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560, maxHeight: 620),
        child: DefaultTabController(
          length: tabs.length,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 8, 0),
              child: Row(children: [
                Icon(isMail ? Icons.mail_outline_rounded : Icons.notifications_none_rounded, color: AppColors.primary),
                const SizedBox(width: 10),
                Expanded(child: Text(isMail ? 'Wiadomości' : 'Powiadomienia', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800))),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
              ]),
            ),
            TabBar(
              isScrollable: tabs.length > 3,
              tabAlignment: tabs.length > 3 ? TabAlignment.start : null,
              tabs: [
                for (final t in tabs)
                  Tab(
                    key: Key('inbox-tab-${t.cat.name}'),
                    icon: Badge(isLabelVisible: count(t.cat) > 0, label: Text('${count(t.cat)}'), child: Icon(t.icon, size: 20)),
                    text: t.label,
                  ),
              ],
            ),
            Flexible(
              child: SizedBox(
                height: 440,
                child: inbox.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('$e', style: const TextStyle(color: AppColors.danger))),
                  data: (d) => TabBarView(children: [for (final t in tabs) _list(t, d, dash)]),
                ),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  /// Budynki: stan na żywo z /dashboard (backend nie zapisuje zdarzeń o skarbcach).
  List<(String, String)> _buildingAlerts(DashboardData? d) => d == null
      ? const []
      : [
          for (final e in d.vaultFills.entries)
            if (e.value >= .95) ('💰', 'Skarbiec „${e.key}” pełny w ${(e.value * 100).round()}% — odbierz w Dzielnicy, zanim przestanie zarabiać.'),
          for (final c in d.brokenCars) ('🔧', 'Auto „${d.carName(c)}” ma zużycie 100% — wymaga naprawy w Garażu.'),
        ];

  Widget _list(_Tab t, InboxData d, DashboardData? dash) {
    final rows = <Widget>[];
    if (t.cat == InboxCat.chat) {
      for (final th in d.threads) {
        rows.add(_row('💬', '${th.nickname}: ${th.mine ? 'Ty: ' : ''}${th.last}', th.at, unread: th.unread > 0));
      }
    } else if (t.cat == InboxCat.buildings) {
      for (final (ic, txt) in _buildingAlerts(dash)) {
        rows.add(_row(ic, txt, null, unread: true));
      }
    } else {
      if (t.cat == InboxCat.crew && dash != null) {
        for (final n in dash.warnNpcs) {
          rows.add(_row('😮‍💨', '$n potrzebuje odpoczynku lub jedzenia.', null, unread: true));
        }
      }
      for (final e in d.events.where((e) => e.cat == t.cat)) {
        rows.add(_row(e.icon, e.text, e.at, unread: !e.read));
      }
    }
    if (rows.isEmpty) return _Empty(tab: t);
    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: rows.length,
      separatorBuilder: (_, _) => const Divider(height: 1, color: AppColors.border),
      itemBuilder: (_, i) => rows[i],
    );
  }

  Widget _row(String icon, String text, int? at, {bool unread = false}) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(icon, style: const TextStyle(fontSize: 18)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(text, style: TextStyle(fontSize: 13, fontWeight: unread ? FontWeight.w700 : FontWeight.w400)),
              if (at != null && at > 0) Text(_ago(at), style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
            ]),
          ),
          if (unread) Container(margin: const EdgeInsets.only(top: 6, left: 6), width: 8, height: 8, decoration: const BoxDecoration(color: AppColors.primary, shape: BoxShape.circle)),
        ]),
      );

  static String _ago(int ms) {
    final d = DateTime.now().difference(DateTime.fromMillisecondsSinceEpoch(ms));
    if (d.inMinutes < 1) return 'przed chwilą';
    if (d.inHours < 1) return '${d.inMinutes} min temu';
    if (d.inDays < 1) return '${d.inHours} h temu';
    return '${d.inDays} d temu';
  }
}

class _Empty extends StatelessWidget {
  const _Empty({required this.tab});
  final _Tab tab;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: AppColors.surfaceLight, shape: BoxShape.circle, border: Border.all(color: AppColors.border)),
              child: Icon(tab.icon, size: 34, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 12),
            Text(tab.empty, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
          ]),
        ),
      );
}
