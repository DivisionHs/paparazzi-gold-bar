import 'package:flutter/material.dart';
import '../models/aniversariante_model.dart';
import '../services/api_service.dart';

enum _EstadoTela { carregando, erro, carregado }

// Painel staff-only: aniversariantes com reserva pra hoje, horário,
// estimativa de convidados (dados do Kommo, persistidos no Supabase desde
// a migration 20260817_01) e a quantidade real já confirmada (contada ao
// vivo em `convidados`). Mesmo padrão de enum de estado já usado em
// register_screen.dart/portaria_screen.dart.
class PainelDiaScreen extends StatefulWidget {
  const PainelDiaScreen({super.key});

  @override
  State<PainelDiaScreen> createState() => _PainelDiaScreenState();
}

class _PainelDiaScreenState extends State<PainelDiaScreen> {
  final _apiService = ApiService();

  _EstadoTela _estado = _EstadoTela.carregando;
  List<AniversarianteHoje> _aniversariantes = [];
  String? _erro;

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() => _estado = _EstadoTela.carregando);
    try {
      final lista = await _apiService.buscarAniversariantesHoje();
      if (!mounted) return;
      setState(() {
        _aniversariantes = lista;
        _estado = _EstadoTela.carregado;
      });
    } catch (erro) {
      if (!mounted) return;
      setState(() {
        _erro = erro.toString();
        _estado = _EstadoTela.erro;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: colorNight,
      appBar: AppBar(
        backgroundColor: colorNight,
        elevation: 0,
        title: const Text('Aniversariantes do Dia', style: TextStyle(color: Colors.white, fontSize: 16)),
        iconTheme: const IconThemeData(color: colorGold),
        actions: [
          IconButton(icon: const Icon(Icons.refresh, color: colorGold), onPressed: _carregar),
        ],
      ),
      body: SafeArea(child: _buildCorpo()),
    );
  }

  Widget _buildCorpo() {
    switch (_estado) {
      case _EstadoTela.carregando:
        return const Center(child: CircularProgressIndicator(color: colorGold));
      case _EstadoTela.erro:
        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, color: colorGold, size: 48),
                const SizedBox(height: 12),
                Text(_erro ?? 'Erro ao carregar.', textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _carregar,
                  style: ElevatedButton.styleFrom(backgroundColor: colorGold, foregroundColor: colorNight),
                  child: const Text('Tentar de novo'),
                ),
              ],
            ),
          ),
        );
      case _EstadoTela.carregado:
        if (_aniversariantes.isEmpty) {
          return const Center(
            child: Text('Nenhum aniversariante com reserva para hoje.', style: TextStyle(color: Colors.white54)),
          );
        }
        return RefreshIndicator(
          onRefresh: _carregar,
          color: colorGold,
          backgroundColor: colorGraphite,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: _aniversariantes.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _buildCard(_aniversariantes[index]),
          ),
        );
    }
  }

  Widget _buildCard(AniversarianteHoje a) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorGraphite.withOpacity(0.8),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colorGold.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: colorGold.withOpacity(0.12), borderRadius: BorderRadius.circular(12)),
            child: Text(
              a.horarioReserva ?? '--:--',
              style: const TextStyle(color: colorGold, fontWeight: FontWeight.bold, fontSize: 13),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(a.nomeCompleto, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(
                  a.estimativaConvidados != null
                      ? '${a.quantidadeConfirmada} confirmados de ~${a.estimativaConvidados} estimados'
                      : '${a.quantidadeConfirmada} confirmados',
                  style: const TextStyle(color: Colors.white60, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
