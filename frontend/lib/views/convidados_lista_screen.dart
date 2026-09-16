import 'package:flutter/material.dart';
import '../models/aniversariante_model.dart';
import '../services/api_service.dart';

enum _EstadoTela { carregando, erro, carregado }

// Lista de convidados confirmados de um aniversariante específico (staff-only),
// aberta ao tocar no nome dele no painel do dia (painel_dia_screen.dart).
class ConvidadosListaScreen extends StatefulWidget {
  final String leadId;
  final String nomeAniversariante;
  final String? horarioReserva;

  const ConvidadosListaScreen({
    super.key,
    required this.leadId,
    required this.nomeAniversariante,
    this.horarioReserva,
  });

  @override
  State<ConvidadosListaScreen> createState() => _ConvidadosListaScreenState();
}

class _ConvidadosListaScreenState extends State<ConvidadosListaScreen> {
  final _apiService = ApiService();

  _EstadoTela _estado = _EstadoTela.carregando;
  List<ConvidadoResumo> _convidados = [];
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
      final lista = await _apiService.buscarConvidadosDoAniversariante(widget.leadId);
      if (!mounted) return;
      setState(() {
        _convidados = lista;
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
        title: Text(
          widget.nomeAniversariante,
          style: const TextStyle(color: Colors.white, fontSize: 16),
        ),
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
        final itensExtras = _convidados.isEmpty ? 2 : 1;
        return RefreshIndicator(
          onRefresh: _carregar,
          color: colorGold,
          backgroundColor: colorGraphite,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: _convidados.length + itensExtras,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              if (index == 0) return _buildCabecalho();
              if (_convidados.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.only(top: 24),
                  child: Center(
                    child: Text('Nenhum convidado confirmado ainda.', style: TextStyle(color: Colors.white54)),
                  ),
                );
              }
              return _buildLinha(_convidados[index - 1]);
            },
          ),
        );
    }
  }

  // Cabeçalho com nome do aniversariante, horário da reserva (já formatado
  // "HH:MM" pelo backend, ver flyer_generator.formatar_horario_exibicao) e a
  // quantidade de convidados confirmados — tudo junto, como pedido pelo
  // usuário, pra não precisar voltar ao painel pra conferir o horário.
  Widget _buildCabecalho() {
    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorGold.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colorGold.withOpacity(0.25)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.nomeAniversariante,
                  style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  widget.horarioReserva != null && widget.horarioReserva!.isNotEmpty
                      ? 'Reserva às ${widget.horarioReserva}'
                      : 'Horário não informado',
                  style: const TextStyle(color: Colors.white60, fontSize: 13),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: colorGold.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              children: [
                Text('${_convidados.length}', style: const TextStyle(color: colorGold, fontWeight: FontWeight.bold, fontSize: 16)),
                const Text('convidados', style: TextStyle(color: Colors.white60, fontSize: 10)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLinha(ConvidadoResumo convidado) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: colorGraphite.withOpacity(0.8),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colorGold.withOpacity(0.15)),
      ),
      child: Row(
        children: [
          const Icon(Icons.person_outline, color: colorGold, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              convidado.nomeCompleto,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}
