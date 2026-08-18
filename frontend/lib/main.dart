import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'views/register_screen.dart';
import 'views/staff_gate.dart';

// Credenciais do Supabase Auth, parametrizadas via --dart-define no build
// (mesmo padrão do API_URL já usado em api_service.dart). É a MESMA
// SUPABASE_URL/SUPABASE_KEY (chave anon) já usada pelo backend — só serve
// pro client de autenticação, os dados continuam passando pelo FastAPI.
const String _supabaseUrl = String.fromEnvironment('SUPABASE_URL');
const String _supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(url: _supabaseUrl, publishableKey: _supabaseAnonKey);

  // Lê os parâmetros direto da URL do navegador. Como o app não usa
  // Navigator 2.0/rotas nomeadas, Uri.base reflete a URL que o navegador
  // carregou ao abrir a página.
  //   - ?token=<UUID>  -> tela pública de cadastro do convidado, SEMPRE
  //                       acessível sem login, mesmo se houver uma sessão
  //                       de funcionário ativa no navegador.
  //   - sem token      -> lado da equipe: StaffGate decide entre login e o
  //                       hub administrativo (Portaria, painel do dia, ...)
  //                       de acordo com a sessão do Supabase Auth.
  final Uri uriAtual = Uri.base;
  final String? tokenAniversariante = uriAtual.queryParameters['token'];

  runApp(MyApp(token: tokenAniversariante));
}

class MyApp extends StatelessWidget {
  final String? token;

  const MyApp({super.key, this.token});

  @override
  Widget build(BuildContext context) {
    final String? tokenAtual = token;

    return MaterialApp(
      title: 'Paparazzi Gold Bar',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
      ),
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('pt', 'BR'),
      ],
      locale: const Locale('pt', 'BR'),
      home: (tokenAtual != null && tokenAtual.isNotEmpty)
          ? RegisterScreen(token: tokenAtual)
          : const StaffGate(),
    );
  }
}