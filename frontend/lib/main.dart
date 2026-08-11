import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'views/register_screen.dart';
import 'views/portaria_screen.dart';

void main() {
  // Lê os parâmetros direto da URL do navegador. Como o app não usa
  // Navigator 2.0/rotas nomeadas, Uri.base reflete a URL que o navegador
  // carregou ao abrir a página.
  //   - ?token=<UUID>      -> tela de cadastro do convidado (padrão)
  //   - ?modo=portaria     -> tela operacional da Portaria Expressa
  final Uri uriAtual = Uri.base;
  final bool modoPortaria = uriAtual.queryParameters['modo'] == 'portaria';
  final String? tokenAniversariante = uriAtual.queryParameters['token'];

  runApp(MyApp(modoPortaria: modoPortaria, token: tokenAniversariante));
}

class MyApp extends StatelessWidget {
  final bool modoPortaria;
  final String? token;

  const MyApp({super.key, this.modoPortaria = false, this.token});

  @override
  Widget build(BuildContext context) {
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
      home: modoPortaria ? const PortariaScreen() : RegisterScreen(token: token),
    );
  }
}