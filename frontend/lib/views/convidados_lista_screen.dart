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
  String? _idConfirmando; // id do convidado com a confirmação de entrada em andamento (desabilita o botão dele só)

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

  // Confirma (ou desfaz, se `convidado.utilizado` já for true) a entrada
  // direto pelo nome na lista -- pedido do usuário pra dar um jeito de
  // marcar quem já entrou sem depender do QR Code (pausado enquanto a
  // integração com o novo ERP é avaliada). Atualiza a linha localmente
  // (via copyWith) em vez de recarregar a lista inteira do backend.
  Future<void> _alternarEntrada(ConvidadoResumo convidado) async {
    final novoValor = !convidado.utilizado;
    setState(() => _idConfirmando = convidado.id);

    try {
      await _apiService.confirmarEntradaConvidado(convidado.id, utilizado: novoValor);
      if (!mounted) return;
      setState(() {
        _convidados = _convidados
            .map((c) => c.id == convidado.id ? c.copyWith(utilizado: novoValor) : c)
            .toList();
      });
    } catch (erro) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(erro.toString()), backgroundColor: Colors.amber[800]),
      );
    } finally {
      if (mounted) setState(() => _idConfirmando = null);
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
  // "HH:MM", ver _formatarHoraCurta em aniversariante_model.dart) e duas
  // contagens lado a lado: quantos confirmaram presença pelo formulário
  // (_convidados.length, como já existia) e quantos já entraram de fato
  // (convidados com `utilizado=true`, mesma coluna marcada na Portaria) —
  // pedido do usuário pra distinguir as duas coisas.
  Widget _buildCabecalho() {
    final totalEntraram = _convidados.where((c) => c.utilizado).length;

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorGold.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colorGold.withOpacity(0.25)),
      ),
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
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(child: _buildEstatistica('${_convidados.length}', 'confirmados\n(formulário)')),
              const SizedBox(width: 10),
              Expanded(child: _buildEstatistica('$totalEntraram', 'já\nentraram')),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildEstatistica(String valor, String legenda) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: colorGold.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        children: [
          Text(valor, style: const TextStyle(color: colorGold, fontWeight: FontWeight.bold, fontSize: 18)),
          Text(legenda, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white60, fontSize: 10, height: 1.2)),
        ],
      ),
    );
  }

  Widget _buildLinha(ConvidadoResumo convidado) {
    final confirmando = _idConfirmando == convidado.id;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: colorGraphite.withOpacity(0.8),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colorGold.withOpacity(0.15)),
      ),
      child: Row(
        children: [
          Icon(
            convidado.utilizado ? Icons.check_circle : Icons.person_outline,
            color: convidado.utilizado ? Colors.greenAccent : colorGold,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              convidado.nomeCompleto,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
          const SizedBox(width: 8),
          _buildBotaoEntrada(convidado, confirmando),
        ],
      ),
    );
  }

  // Botão de confirmar entrada (ou chip "Entrou", tocável pra desfazer uma
  // confirmação feita por engano) -- pedido do usuário: dar um jeito de
  // marcar a entrada do convidado direto pelo nome, sem QR Code.
  Widget _buildBotaoEntrada(ConvidadoResumo convidado, bool confirmando) {
    if (confirmando) {
      return const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2, color: colorGold),
      );
    }

    if (convidado.utilizado) {
      return OutlinedButton.icon(
        onPressed: () => _alternarEntrada(convidado),
        style: OutlinedButton.styleFrom(
          foregroundColor: Colors.greenAccent,
          side: const BorderSide(color: Colors.greenAccent),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        icon: const Icon(Icons.check, size: 16),
        label: const Text('Entrou', style: TextStyle(fontSize: 12)),
      );
    }

    return ElevatedButton(
      onPressed: () => _alternarEntrada(convidado),
      style: ElevatedButton.styleFrom(
        backgroundColor: colorGold,
        foregroundColor: colorNight,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      child: const Text('Confirmar entrada', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
    );
  }
}
