import 'package:flutter/material.dart';
import '../models/aniversariante_model.dart';
import '../services/api_service.dart';
import 'convidados_lista_screen.dart';

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
  DateTime _dataSelecionada = DateTime.now();

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);

  bool get _eHoje => _ehMesmoDia(_dataSelecionada, DateTime.now());

  bool _ehMesmoDia(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() => _estado = _EstadoTela.carregando);
    try {
      final lista = await _apiService.buscarAniversariantesHoje(data: _dataSelecionada);
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

  // Abre o seletor de data (pedido do usuário -- ver outros dias, não só
  // hoje) e recarrega a lista pra data escolhida.
  Future<void> _escolherData(BuildContext context) async {
    final DateTime? escolhida = await showDatePicker(
      context: context,
      locale: const Locale('pt', 'BR'),
      initialDate: _dataSelecionada,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      builder: (context, child) {
        // Mesma paleta escura/dourada do resto do app (ver o mesmo padrão em
        // register_screen.dart::_selectDate, usado no campo de data de
        // nascimento do convidado) -- garante que o calendário do
        // showDatePicker não caia no tema claro padrão do Flutter.
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: colorGold,
              onPrimary: colorNight,
              surface: colorGraphite,
              onSurface: Colors.white,
            ),
            dialogBackgroundColor: colorNight,
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
    );

    if (escolhida == null || !mounted) return;

    setState(() => _dataSelecionada = escolhida);
    _carregar();
  }

  void _irParaHoje() {
    setState(() => _dataSelecionada = DateTime.now());
    _carregar();
  }

  // Data completa (DD/MM/AAAA) -- usada só em textos de corpo, onde tem
  // espaço sobrando (ex.: mensagem de lista vazia).
  String _formatarTituloData(DateTime data) {
    final dia = data.day.toString().padLeft(2, '0');
    final mes = data.month.toString().padLeft(2, '0');
    return '$dia/$mes/${data.year}';
  }

  // Data curta (DD/MM, sem ano) -- usada no título da AppBar, que divide
  // espaço com até 3 ícones de ação; a versão com ano/"Aniversariantes de"
  // estourava a largura em telas de celular e cortava em "...".
  String _formatarDataCurta(DateTime data) {
    final dia = data.day.toString().padLeft(2, '0');
    final mes = data.month.toString().padLeft(2, '0');
    return '$dia/$mes';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: colorNight,
      appBar: AppBar(
        backgroundColor: colorNight,
        elevation: 0,
        title: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            _eHoje ? 'Aniversariantes do Dia' : 'Aniversariantes — ${_formatarDataCurta(_dataSelecionada)}',
            style: const TextStyle(color: Colors.white, fontSize: 16),
          ),
        ),
        iconTheme: const IconThemeData(color: colorGold),
        actions: [
          if (!_eHoje)
            IconButton(
              icon: const Icon(Icons.today, color: colorGold),
              tooltip: 'Voltar para hoje',
              onPressed: _irParaHoje,
            ),
          IconButton(
            icon: const Icon(Icons.calendar_month, color: colorGold),
            tooltip: 'Escolher outra data',
            onPressed: () => _escolherData(context),
          ),
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
          return Center(
            child: Text(
              _eHoje
                  ? 'Nenhum aniversariante com reserva para hoje.'
                  : 'Nenhum aniversariante com reserva em ${_formatarTituloData(_dataSelecionada)}.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white54),
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: _carregar,
          color: colorGold,
          backgroundColor: colorGraphite,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: _aniversariantes.length + 1,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              if (index == 0) return _buildResumo();
              return _buildCard(_aniversariantes[index - 1]);
            },
          ),
        );
    }
  }

  // Resumo simples no topo: quantidade de aniversariantes de hoje (contagem
  // de registros em `aniversariantes`) e a soma dos convidados estimados —
  // esse segundo número vem direto do CRM (Custom Field "Estimativa de
  // Convidados", já sincronizado em `estimativa_convidados`), não da
  // contagem real de confirmações no Supabase (essa fica só no card
  // individual, ver _buildCard).
  Widget _buildResumo() {
    final totalAniversariantes = _aniversariantes.length;
    final totalConvidadosEstimados = _aniversariantes.fold<int>(
      0,
      (soma, a) => soma + (a.estimativaConvidados ?? 0),
    );

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: colorGold.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colorGold.withOpacity(0.25)),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildResumoItem(
              Icons.cake_outlined,
              '$totalAniversariantes',
              _eHoje ? 'aniversariantes hoje' : 'aniversariantes no dia',
            ),
          ),
          Container(width: 1, height: 36, color: colorGold.withOpacity(0.2)),
          Expanded(
            child: _buildResumoItem(Icons.groups_outlined, '$totalConvidadosEstimados', 'convidados (CRM)'),
          ),
        ],
      ),
    );
  }

  Widget _buildResumoItem(IconData icone, String valor, String legenda) {
    return Column(
      children: [
        Icon(icone, color: colorGold, size: 20),
        const SizedBox(height: 6),
        Text(valor, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
        Text(legenda, style: const TextStyle(color: Colors.white60, fontSize: 11), textAlign: TextAlign.center),
      ],
    );
  }

  Widget _buildCard(AniversarianteHoje a) {
    return Material(
      color: colorGraphite.withOpacity(0.8),
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ConvidadosListaScreen(
              leadId: a.leadId,
              nomeAniversariante: a.nomeCompleto,
              horarioReserva: a.horarioReserva,
            ),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
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
              const Icon(Icons.chevron_right, color: Colors.white38),
            ],
          ),
        ),
      ),
    );
  }
}
