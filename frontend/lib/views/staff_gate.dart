import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'login_screen.dart';
import 'hub_screen.dart';

// Portão do lado da equipe: escuta a sessão do Supabase Auth e alterna
// entre LoginScreen (sem sessão) e HubScreen (com sessão) sozinho, sem
// nenhum pacote de gerenciamento de estado — só StreamBuilder nativo sobre
// auth.onAuthStateChange, mesmo padrão simples de StatefulWidget já usado
// no resto do app. Só é usado quando a URL NÃO tem `?token=` (esse caso
// continua indo direto pro RegisterScreen, público, em main.dart).
class StaffGate extends StatelessWidget {
  const StaffGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, snapshot) {
        final sessao = Supabase.instance.client.auth.currentSession;
        if (sessao == null) {
          return const LoginScreen();
        }
        return const HubScreen();
      },
    );
  }
}
