import 'package:flutter/material.dart';
import '../models/aniversariante_model.dart';
import '../services/api_service.dart';

enum _EstadoTela { carregando, erro, carregado }

// Período rápido do filtro (decisão de 07/10/2026, ver CLAUDE.md 4.11):
// só os 4 presets abaixo -- nada de período customizado/calendário ainda,
// isso faz parte do "Dashboard completo" maior, que fica pra próxima fase
// (condicionado a contrato mensal). `intervalo` devolve null/null pra
// "tudo" (mantém o comportamento cumulativo de sempre).
enum _Periodo { hoje, semana, mes, tudo }

extension on _Periodo {
  String get rotulo => switch (this) {
        _Periodo.hoje => 'Hoje',
        _Periodo.semana => 'Últimos 7 dias',
        _Periodo.mes => 'Este mês',
        _Periodo.tudo => 'Tudo',
      };

  (DateTime?, DateTime?) get intervalo {
    final hoje = DateTime.now();
    switch (this) {
      case _Periodo.hoje:
        return (hoje, hoje);
      case _Periodo.semana:
        return (hoje.subtract(const Duration(days: 6)), hoje);
      case _Periodo.mes:
        final inicioMes = DateTime(hoje.year, hoje.month, 1);
        final fimMes = DateTime(hoje.year, hoje.month + 1, 0);
        return (inicioMes, fimMes);
      case _Periodo.tudo:
        return (null, null);
    }
  }
}

// Dashboard geral do login admin (decisão de 29/09/2026, ver CLAUDE.md
// 4.10): três números -- agendamentos já processados, convidados
// aproximados (soma vinda do Kommo) e convidados confirmados de fato --
// com filtro rápido de período (decisão de 07/10/2026, ver CLAUDE.md
// 4.11; padrão "Tudo", cumulativo desde sempre, igual antes). Só aparece
// no Hub pro login admin (ver HubScreen); a rota no backend também é
// protegida (GET /aniversariantes/estatisticas, `exigir_admin`).
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);
  static const Color colorSoftGold = Color(0xFFF1D38E);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _apiService = ApiService();

  _EstadoTela _estado = _EstadoTela.carregando;
  EstatisticasGerais? _estatisticas;
  String? _erro;
  _Periodo _periodo = _Periodo.tudo;

  static const Color colorNight = DashboardScreen.colorNight;
  static const Color colorGraphite = DashboardScreen.colorGraphite;
  static const Color colorGold = DashboardScreen.colorGold;
  static const Color colorSoftGold = DashboardScreen.colorSoftGold;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() => _estado = _EstadoTela.carregando);
    try {
      final (inicio, fim) = _periodo.intervalo;
      final estatisticas = await _apiService.buscarEstatisticasGerais(inicio: inicio, fim: fim);
      if (!mounted) return;
      setState(() {
        _estatisticas = estatisticas;
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

  void _selecionarPeriodo(_Periodo periodo) {
    if (periodo == _periodo) return;
    setState(() => _periodo = periodo);
    _carregar();
  }

  // Filtro rápido de período -- linha de chips simples (sem calendário/
  // período customizado, ver nota na declaração de _Periodo).
  Widget _buildFiltroPeriodo() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _Periodo.values.map((periodo) {
        final selecionado = periodo == _periodo;
        return ChoiceChip(
          label: Text(periodo.rotulo),
          selected: selecionado,
          onSelected: (_) => _selecionarPeriodo(periodo),
          backgroundColor: colorGraphite.withOpacity(0.8),
          selectedColor: colorGold,
          labelStyle: TextStyle(
            color: selecionado ? colorNight : Colors.white70,
            fontSize: 12,
            fontWeight: selecionado ? FontWeight.bold : FontWeight.normal,
          ),
          side: BorderSide(color: colorGold.withOpacity(selecionado ? 1 : 0.25)),
          showCheckmark: false,
        );
      }).toList(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: colorNight,
      appBar: AppBar(
        backgroundColor: colorNight,
        elevation: 0,
        title: const Text('Dashboard', style: TextStyle(color: Colors.white, fontSize: 16)),
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
        final estatisticas = _estatisticas!;
        return RefreshIndicator(
          onRefresh: _carregar,
          color: colorGold,
          backgroundColor: colorGraphite,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const Text(
                'VISÃO GERAL',
                style: TextStyle(color: colorSoftGold, fontSize: 12, letterSpacing: 2, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 4),
              Text(
                _periodo == _Periodo.tudo
                    ? 'Números acumulados desde o início do fluxo automático.'
                    : 'Números do período selecionado: ${_periodo.rotulo.toLowerCase()}.',
                style: const TextStyle(color: Colors.white38, fontSize: 12),
              ),
              const SizedBox(height: 16),
              _buildFiltroPeriodo(),
              const SizedBox(height: 20),
              _StatTile(
                icone: Icons.event_available_outlined,
                valor: '${estatisticas.totalAgendamentos}',
                titulo: 'Agendamentos realizados',
                subtitulo: 'Comemorações com flyer já processado',
              ),
              const SizedBox(height: 14),
              _StatTile(
                icone: Icons.groups_outlined,
                valor: '${estatisticas.totalConvidadosEstimados}',
                titulo: 'Convidados aproximados',
                subtitulo: 'Estimativa informada pelos aniversariantes',
              ),
              const SizedBox(height: 14),
              _StatTile(
                icone: Icons.check_circle_outline,
                valor: '${estatisticas.totalConvidadosConfirmados}',
                titulo: 'Convidados confirmados',
                subtitulo: 'Já preencheram o formulário de presença',
              ),
              const SizedBox(height: 24),
              Row(
                children: const [
                  Icon(Icons.info_outline, color: Colors.white24, size: 14),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Mais detalhamento por reserva e exportação chegam numa próxima fase.',
                      style: TextStyle(color: Colors.white24, fontSize: 11),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
    }
  }
}

// Tile de estatística: número grande em destaque (maior peso visual da
// tela) + título/subtítulo em texto neutro -- hierarquia por tamanho/peso,
// não por cor (o dourado fica só no ícone e no número, nunca no texto de
// apoio). Layout em coluna cheia (não em grade 3-colunas) porque em tela de
// celular 3 números lado a lado ficam apertados demais pra ler rápido.
class _StatTile extends StatelessWidget {
  final IconData icone;
  final String valor;
  final String titulo;
  final String subtitulo;

  const _StatTile({
    required this.icone,
    required this.valor,
    required this.titulo,
    required this.subtitulo,
  });

  static const Color colorGraphite = DashboardScreen.colorGraphite;
  static const Color colorGold = DashboardScreen.colorGold;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: colorGraphite.withOpacity(0.8),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colorGold.withOpacity(0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: colorGold.withOpacity(0.12), borderRadius: BorderRadius.circular(14)),
            child: Icon(icone, color: colorGold, size: 26),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(titulo, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(subtitulo, style: const TextStyle(color: Colors.white38, fontSize: 11)),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text(
            valor,
            style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
