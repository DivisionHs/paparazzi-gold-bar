import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'portaria_screen.dart';
import 'painel_dia_screen.dart';

// Hub administrativo pós-login: ponto de entrada único de tudo que é
// operacional (Portaria, painel de aniversariantes do dia, ...). Navegação
// simples via Navigator 1.0 (MaterialPageRoute) — sem rotas nomeadas, mesmo
// padrão já usado no resto do app.
class HubScreen extends StatelessWidget {
  const HubScreen({super.key});

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);
  static const Color colorSoftGold = Color(0xFFF1D38E);

  Future<void> _sair(BuildContext context) async {
    await Supabase.instance.client.auth.signOut();
    // staff_gate.dart escuta onAuthStateChange e volta pro LoginScreen sozinho.
  }

  @override
  Widget build(BuildContext context) {
    final email = Supabase.instance.client.auth.currentUser?.email ?? '';

    return Scaffold(
      backgroundColor: colorNight,
      appBar: AppBar(
        backgroundColor: colorNight,
        elevation: 0,
        title: const Text(
          'PAPARAZZI GOLD BAR',
          style: TextStyle(color: colorSoftGold, fontSize: 14, letterSpacing: 3, fontWeight: FontWeight.w300),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: colorGold),
            tooltip: 'Sair',
            onPressed: () => _sair(context),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(email, style: const TextStyle(color: Colors.white54, fontSize: 13)),
              const SizedBox(height: 24),
              _CardHub(
                icone: Icons.qr_code_scanner,
                titulo: 'Portaria Expressa',
                subtitulo: 'Ler QR Code ou buscar convidado por CPF',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const PortariaScreen()),
                ),
              ),
              const SizedBox(height: 16),
              _CardHub(
                icone: Icons.cake_outlined,
                titulo: 'Aniversariantes do Dia',
                subtitulo: 'Reservas de hoje e convidados confirmados',
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const PainelDiaScreen()),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CardHub extends StatelessWidget {
  final IconData icone;
  final String titulo;
  final String subtitulo;
  final VoidCallback onTap;

  const _CardHub({
    required this.icone,
    required this.titulo,
    required this.subtitulo,
    required this.onTap,
  });

  static const Color colorGraphite = HubScreen.colorGraphite;
  static const Color colorGold = HubScreen.colorGold;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: colorGraphite.withOpacity(0.8),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: colorGold.withOpacity(0.25)),
          ),
          child: Row(
            children: [
              Icon(icone, color: colorGold, size: 32),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(titulo, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(subtitulo, style: const TextStyle(color: Colors.white60, fontSize: 12)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.white38),
            ],
          ),
        ),
      ),
    );
  }
}
