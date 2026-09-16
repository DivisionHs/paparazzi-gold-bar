import 'package:flutter/material.dart';

// Placeholder genérico para funcionalidades temporariamente desativadas no
// Hub (ex.: Portaria/QR Code, pausada em 15/09/2026 até a avaliação da API
// do novo ERP da Paparazzi). Mesma paleta/moldura do resto do app.
class EmDesenvolvimentoScreen extends StatelessWidget {
  final String titulo;
  final String mensagem;

  const EmDesenvolvimentoScreen({
    super.key,
    required this.titulo,
    this.mensagem = 'Esta funcionalidade está temporariamente fora do ar.\nEm desenvolvimento.',
  });

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGold = Color(0xFFD4A94F);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: colorNight,
      appBar: AppBar(
        backgroundColor: colorNight,
        elevation: 0,
        title: Text(titulo, style: const TextStyle(color: Colors.white, fontSize: 16)),
        iconTheme: const IconThemeData(color: colorGold),
      ),
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.construction_outlined, color: colorGold, size: 56),
                const SizedBox(height: 20),
                Text(
                  mensagem,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70, fontSize: 15, height: 1.4),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
