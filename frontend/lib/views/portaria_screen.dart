import 'dart:async';
import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:mask_text_input_formatter/mask_text_input_formatter.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../models/validacao_qr_model.dart';
import '../services/api_service.dart';

// Estado visual da tela: escaneando (câmera ativa) ou um dos três resultados
// possíveis devolvidos por POST /convidados/validar-qr.
enum _EstadoPortaria { escaneando, liberado, jaUtilizado, invalido }

// Helpers de formatação compartilhados pela tela cheia de resultado e pelo
// modal de busca manual, evitando duplicar a mesma lógica nos dois lugares.
String? _formatarDataHora(String? isoString) {
  if (isoString == null) return null;
  try {
    final data = DateTime.parse(isoString).toLocal();
    final dia = data.day.toString().padLeft(2, '0');
    final mes = data.month.toString().padLeft(2, '0');
    final hora = data.hour.toString().padLeft(2, '0');
    final minuto = data.minute.toString().padLeft(2, '0');
    return 'Entrada em $dia/$mes às $hora:$minuto';
  } catch (_) {
    return isoString;
  }
}

String _formatarCpf(String? cpf) {
  final digitos = (cpf ?? '').replaceAll(RegExp(r'\D'), '');
  if (digitos.length != 11) return cpf ?? '';
  return '${digitos.substring(0, 3)}.${digitos.substring(3, 6)}.${digitos.substring(6, 9)}-${digitos.substring(9, 11)}';
}

class PortariaScreen extends StatefulWidget {
  const PortariaScreen({super.key});

  @override
  State<PortariaScreen> createState() => _PortariaScreenState();
}

class _PortariaScreenState extends State<PortariaScreen> {
  final _apiService = ApiService();

  // noDuplicates evita que o mesmo código dispare onDetect várias vezes
  // seguidas enquanto ele continua visível no quadro da câmera.
  final MobileScannerController _controller = MobileScannerController(
    detectionSpeed: DetectionSpeed.noDuplicates,
  );

  _EstadoPortaria _estado = _EstadoPortaria.escaneando;
  ValidacaoQrResultado? _resultado;
  bool _processando = false; // trava contra chamadas simultâneas à API
  Timer? _timerReset;

  // Confete dura o mesmo tanto que o reset automático de 3s da tela de resultado.
  final ConfettiController _confettiController = ConfettiController(
    duration: const Duration(seconds: 3),
  );

  static const Color _corFundoScan = Color(0xFF090909);
  static const Color _corDestaque = Color(0xFFD4A94F);
  static const Color _corLiberado = Color(0xFF2ECC71);
  static const Color _corJaUtilizado = Color(0xFFE74C3C);
  static const Color _corInvalido = Color(0xFFE67E22);
  static const Color _corVip = Color(0xFFFFD700);

  @override
  void dispose() {
    _timerReset?.cancel();
    _controller.dispose();
    _confettiController.dispose();
    super.dispose();
  }

  // Chamado a cada código detectado pela câmera. Ignora novos disparos
  // enquanto uma requisição anterior ainda está em andamento ou enquanto
  // a tela de resultado (verde/vermelho/laranja) está em exibição.
  Future<void> _aoDetectarCodigo(BarcodeCapture captura) async {
    if (_processando || _estado != _EstadoPortaria.escaneando) return;
    if (captura.barcodes.isEmpty) return;

    final String? token = captura.barcodes.first.rawValue;
    if (token == null || token.isEmpty) return;

    setState(() => _processando = true);

    try {
      final resultado = await _apiService.validarQrCode(token);
      if (!mounted) return;
      _mostrarResultado(resultado);
    } catch (erro) {
      if (!mounted) return;
      _mostrarResultado(ValidacaoQrResultado(status: 'INVALIDO', mensagem: erro.toString()));
    } finally {
      if (mounted) setState(() => _processando = false);
    }
  }

  void _mostrarResultado(ValidacaoQrResultado resultado) {
    final _EstadoPortaria novoEstado;
    switch (resultado.status) {
      case 'LIBERADO':
        novoEstado = _EstadoPortaria.liberado;
        break;
      case 'JA_UTILIZADO':
        novoEstado = _EstadoPortaria.jaUtilizado;
        break;
      default:
        novoEstado = _EstadoPortaria.invalido;
    }

    setState(() {
      _resultado = resultado;
      _estado = novoEstado;
    });

    // Cliente lido é o próprio aniversariante da lista: solta os confetes.
    if (resultado.eAniversariante) {
      _confettiController.play();
    }

    // Reset automático: depois de 3s a tela volta sozinha para o modo leitura,
    // liberando o porteiro para bipar o próximo convidado sem precisar tocar na tela.
    _timerReset?.cancel();
    _timerReset = Timer(const Duration(seconds: 3), _voltarParaEscaneamento);
  }

  void _voltarParaEscaneamento() {
    _timerReset?.cancel();
    if (!mounted) return;
    setState(() {
      _estado = _EstadoPortaria.escaneando;
      _resultado = null;
    });
  }

  // Abre o modal de contingência. Se o porteiro confirmar a entrada manual
  // por lá, o modal devolve o ValidacaoQrResultado ao fechar e a tela cheia
  // de resultado (verde/vermelho/laranja) é exibida aqui, do mesmo jeito que
  // aconteceria com uma leitura de QR Code normal.
  Future<void> _abrirBuscaManual() async {
    final resultado = await showModalBottomSheet<ValidacaoQrResultado>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF121212),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => const _BuscaManualModal(),
    );

    if (resultado != null) {
      _mostrarResultado(resultado);
    }
  }

  @override
  Widget build(BuildContext context) {
    return _estado == _EstadoPortaria.escaneando ? _buildTelaScanner() : _buildTelaResultado();
  }

  // ---------------------------------------------------------------------
  // MODO SCAN — câmera em tela cheia com visor guia central
  // ---------------------------------------------------------------------
  Widget _buildTelaScanner() {
    return Scaffold(
      backgroundColor: _corFundoScan,
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _aoDetectarCodigo,
            errorBuilder: (context, error) => _buildErroCamera(error),
          ),
          _buildVisorGuia(),
          _buildCabecalho(),
          if (_processando) _buildIndicadorProcessando(),
        ],
      ),
      floatingActionButton: FloatingActionButton.large(
        heroTag: 'busca-manual',
        backgroundColor: _corDestaque,
        foregroundColor: Colors.black,
        onPressed: _abrirBuscaManual,
        tooltip: 'Busca manual por CPF',
        child: const Icon(Icons.search, size: 32),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  Widget _buildCabecalho() {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        child: Column(
          children: [
            const Text(
              'PORTARIA EXPRESSA',
              style: TextStyle(
                color: _corDestaque,
                fontSize: 16,
                fontWeight: FontWeight.bold,
                letterSpacing: 3,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Aponte a câmera para o QR Code do convidado',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white.withOpacity(0.85), fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVisorGuia() {
    return Center(
      child: Container(
        width: 260,
        height: 260,
        decoration: BoxDecoration(
          border: Border.all(color: _corDestaque, width: 3),
          borderRadius: BorderRadius.circular(24),
        ),
      ),
    );
  }

  Widget _buildIndicadorProcessando() {
    return Container(
      color: Colors.black.withOpacity(0.55),
      child: const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: _corDestaque),
            SizedBox(height: 16),
            Text(
              'Validando...',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErroCamera(MobileScannerException error) {
    return Container(
      color: _corFundoScan,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.videocam_off, color: Colors.white70, size: 56),
              const SizedBox(height: 16),
              const Text(
                'Não foi possível acessar a câmera.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Verifique se a permissão de câmera foi concedida ao navegador.\n(${error.errorCode.name})',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white60, fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------
  // MODO RESPOSTA — LIBERADO (verde) / JA_UTILIZADO (vermelho) / INVALIDO (laranja)
  // ou, se o CPF lido bater com o do aniversariante da lista, a tela VIP dourada.
  // ---------------------------------------------------------------------
  Widget _buildTelaResultado() {
    final resultado = _resultado;

    if (resultado != null && resultado.eAniversariante) {
      return _buildTelaVip(resultado);
    }

    // Configuração padrão cobre o caso INVALIDO; os outros dois casos sobrescrevem abaixo.
    Color corFundo = _corInvalido;
    IconData icone = Icons.help_outline;
    String titulo = 'QR CODE NÃO ENCONTRADO';
    List<Widget> detalhes = [
      _linhaDetalhe(resultado?.mensagem ?? 'QR Code inválido ou não encontrado nesta lista.'),
    ];

    if (_estado == _EstadoPortaria.liberado) {
      corFundo = _corLiberado;
      icone = Icons.check_circle;
      titulo = 'ENTRADA LIBERADA';
      detalhes = [
        if (resultado?.nomeCompleto != null) _linhaDetalhe(resultado!.nomeCompleto!, destaque: true),
        if (resultado?.cpf != null) _linhaDetalhe(_formatarCpf(resultado!.cpf)),
        if (resultado?.nomeAniversariante != null)
          _linhaDetalhe('Lista de Aniversário: ${resultado!.nomeAniversariante}'),
      ];
    } else if (_estado == _EstadoPortaria.jaUtilizado) {
      corFundo = _corJaUtilizado;
      icone = Icons.error;
      titulo = 'ENTRADA JÁ REALIZADA';
      detalhes = [
        if (resultado?.nomeCompleto != null) _linhaDetalhe(resultado!.nomeCompleto!, destaque: true),
        if (resultado?.cpf != null) _linhaDetalhe(_formatarCpf(resultado!.cpf)),
        if (_formatarDataHora(resultado?.dataHoraEntrada) != null)
          _linhaDetalhe(_formatarDataHora(resultado!.dataHoraEntrada)!),
        if (resultado?.nomeAniversariante != null)
          _linhaDetalhe('Lista de Aniversário: ${resultado!.nomeAniversariante}'),
      ];
    }

    return GestureDetector(
      // Toque na tela acelera o retorno ao scanner, sem precisar esperar os 3s.
      onTap: _voltarParaEscaneamento,
      child: Scaffold(
        backgroundColor: corFundo,
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icone, color: Colors.white, size: 120),
                  const SizedBox(height: 24),
                  Text(
                    titulo,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 34,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(height: 16),
                  ...detalhes,
                  const SizedBox(height: 48),
                  const Text(
                    'Toque na tela para voltar ao scanner',
                    style: TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _linhaDetalhe(String texto, {bool destaque = false}) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(
        texto,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: Colors.white,
          fontSize: destaque ? 24 : 18,
          fontWeight: destaque ? FontWeight.bold : FontWeight.w600,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------
  // MODO RESPOSTA VIP — o próprio aniversariante da lista foi lido na portaria.
  // Fundo dourado, texto escuro de alto contraste e confetes.
  // ---------------------------------------------------------------------
  Widget _buildTelaVip(ValidacaoQrResultado resultado) {
    final nome = resultado.nomeAniversariante ?? resultado.nomeCompleto ?? '';
    final cpf = resultado.cpfAniversariante ?? resultado.cpf;

    return GestureDetector(
      onTap: _voltarParaEscaneamento,
      child: Scaffold(
        backgroundColor: _corVip,
        body: Stack(
          children: [
            SafeArea(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Text(
                        '🎉 ANIVERSARIANTE DA NOITE',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.black,
                          fontSize: 30,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 24),
                      Text(
                        nome,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.black,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (cpf != null) ...[
                        const SizedBox(height: 6),
                        Text(
                          _formatarCpf(cpf),
                          style: const TextStyle(
                            color: Colors.black87,
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                      const SizedBox(height: 48),
                      const Text(
                        'Toque na tela para voltar ao scanner',
                        style: TextStyle(color: Colors.black54, fontSize: 13),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Align(
              alignment: Alignment.topCenter,
              child: ConfettiWidget(
                confettiController: _confettiController,
                blastDirectionality: BlastDirectionality.explosive,
                shouldLoop: false,
                numberOfParticles: 40,
                gravity: 0.3,
                colors: const [Colors.amber, Colors.white, Colors.black87, Colors.deepOrange],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ===========================================================================
// MODAL DE CONTINGÊNCIA — Busca manual por CPF
// ===========================================================================
class _BuscaManualModal extends StatefulWidget {
  const _BuscaManualModal();

  @override
  State<_BuscaManualModal> createState() => _BuscaManualModalState();
}

class _BuscaManualModalState extends State<_BuscaManualModal> {
  final _apiService = ApiService();
  final _cpfController = TextEditingController();
  final _cpfFormatter = MaskTextInputFormatter(
    mask: '###.###.###-##',
    filter: {"#": RegExp(r'[0-9]')},
  );

  bool _buscando = false;
  bool _confirmandoEntrada = false;
  String? _mensagemErro;
  String? _erroConfirmacao;
  ConvidadoEncontrado? _convidadoEncontrado;

  final ConfettiController _confettiController = ConfettiController(
    duration: const Duration(seconds: 3),
  );

  static const Color _corDestaque = Color(0xFFD4A94F);
  static const Color _corLiberado = Color(0xFF2ECC71);
  static const Color _corJaUtilizado = Color(0xFFE74C3C);
  static const Color _corVip = Color(0xFFFFD700);

  Future<void> _buscar() async {
    final cpfLimpo = _cpfController.text.replaceAll(RegExp(r'\D'), '');

    if (cpfLimpo.length != 11) {
      setState(() {
        _mensagemErro = 'Digite os 11 dígitos do CPF para buscar.';
        _convidadoEncontrado = null;
      });
      return;
    }

    setState(() {
      _buscando = true;
      _mensagemErro = null;
      _erroConfirmacao = null;
      _convidadoEncontrado = null;
    });

    try {
      final convidado = await _apiService.buscarConvidadoPorCpf(cpfLimpo);
      if (!mounted) return;
      setState(() => _convidadoEncontrado = convidado);
      if (convidado.eAniversariante) {
        _confettiController.play();
      }
    } catch (erro) {
      if (!mounted) return;
      setState(() => _mensagemErro = erro.toString());
    } finally {
      if (mounted) setState(() => _buscando = false);
    }
  }

  // Libera a entrada direto pelo resultado da busca manual, reaproveitando o
  // mesmo contrato de validação usado pela leitura de QR Code (POST /convidados/validar-qr).
  // Ao ter sucesso, fecha o modal devolvendo o resultado para a tela cheia.
  Future<void> _confirmarEntradaManual(ConvidadoEncontrado convidado) async {
    setState(() {
      _confirmandoEntrada = true;
      _erroConfirmacao = null;
    });

    try {
      final resultado = await _apiService.validarQrCode(convidado.qrCodeToken);
      if (!mounted) return;
      Navigator.of(context).pop(resultado);
    } catch (erro) {
      if (!mounted) return;
      setState(() => _erroConfirmacao = erro.toString());
    } finally {
      if (mounted) setState(() => _confirmandoEntrada = false);
    }
  }

  @override
  void dispose() {
    _cpfController.dispose();
    _confettiController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 24,
        bottom: 24 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.white24,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
          const Text(
            'Busca Manual por CPF',
            style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Contingência para quando o convidado não tiver o QR Code em mãos.',
            style: TextStyle(color: Colors.white60, fontSize: 14),
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _cpfController,
            inputFormatters: [_cpfFormatter],
            keyboardType: TextInputType.number,
            autofocus: true,
            style: const TextStyle(color: Colors.white, fontSize: 18),
            decoration: InputDecoration(
              labelText: 'CPF do convidado',
              labelStyle: const TextStyle(color: Colors.white70),
              hintText: '000.000.000-00',
              hintStyle: const TextStyle(color: Colors.white30),
              prefixIcon: const Icon(Icons.badge, color: _corDestaque),
              filled: true,
              fillColor: Colors.white.withOpacity(0.05),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
            onSubmitted: (_) => _buscar(),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 56,
            child: ElevatedButton(
              onPressed: _buscando ? null : _buscar,
              style: ElevatedButton.styleFrom(
                backgroundColor: _corDestaque,
                foregroundColor: Colors.black,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _buscando
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                    )
                  : const Text(
                      'BUSCAR CONVIDADO',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
            ),
          ),
          const SizedBox(height: 20),
          if (_mensagemErro != null)
            Text(
              _mensagemErro!,
              style: const TextStyle(color: Colors.redAccent, fontSize: 14),
            ),
          if (_convidadoEncontrado != null) _buildResultadoBusca(_convidadoEncontrado!),
          const SizedBox(height: 12),
        ],
      ),
    );
  }

  Widget _buildResultadoBusca(ConvidadoEncontrado convidado) {
    if (convidado.eAniversariante) {
      return _buildResultadoVipBusca(convidado);
    }

    final jaEntrou = convidado.utilizado;
    final corResultado = jaEntrou ? _corJaUtilizado : _corLiberado;
    final horarioEntrada = _formatarDataHora(convidado.dataHoraEntrada);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: corResultado.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: corResultado),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            convidado.nomeCompleto,
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            _formatarCpf(convidado.cpf),
            style: const TextStyle(color: Colors.white70, fontSize: 14),
          ),
          if (convidado.nomeAniversariante != null) ...[
            const SizedBox(height: 6),
            Text(
              'Lista de Aniversário: ${convidado.nomeAniversariante}',
              style: const TextStyle(color: _corDestaque, fontSize: 13, fontWeight: FontWeight.w700),
            ),
          ],
          const SizedBox(height: 8),
          Text(
            jaEntrou
                ? (horarioEntrada ?? 'Já deu entrada anteriormente.')
                : 'Ainda não deu entrada nesta lista.',
            style: TextStyle(
              color: jaEntrou ? Colors.white70 : _corLiberado,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (!jaEntrou) ...[
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed: _confirmandoEntrada ? null : () => _confirmarEntradaManual(convidado),
                style: ElevatedButton.styleFrom(
                  backgroundColor: _corLiberado,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                icon: _confirmandoEntrada
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                      )
                    : const Icon(Icons.check_circle_outline),
                label: const Text(
                  'CONFIRMAR ENTRADA MANUAL',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
          if (_erroConfirmacao != null) ...[
            const SizedBox(height: 8),
            Text(
              _erroConfirmacao!,
              style: const TextStyle(color: Colors.redAccent, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }

  // Card VIP dourado exibido quando o CPF buscado é o do próprio aniversariante
  // da lista. Mesma trava de clique múltiplo e botão de confirmação manual do
  // card normal, só que com a identidade visual de destaque + confetes.
  Widget _buildResultadoVipBusca(ConvidadoEncontrado convidado) {
    final jaEntrou = convidado.utilizado;
    final nome = convidado.nomeAniversariante ?? convidado.nomeCompleto;
    final cpf = convidado.cpfAniversariante ?? convidado.cpf;

    return Stack(
      clipBehavior: Clip.none,
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: _corVip,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.black87, width: 2),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '🎉 ANIVERSARIANTE DA NOITE',
                style: TextStyle(color: Colors.black, fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                nome,
                style: const TextStyle(color: Colors.black, fontSize: 17, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 2),
              Text(
                _formatarCpf(cpf),
                style: const TextStyle(color: Colors.black87, fontSize: 14, fontWeight: FontWeight.w600),
              ),
              if (!jaEntrou) ...[
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton.icon(
                    onPressed: _confirmandoEntrada ? null : () => _confirmarEntradaManual(convidado),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.black87,
                      foregroundColor: _corVip,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: _confirmandoEntrada
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: _corVip),
                          )
                        : const Icon(Icons.celebration),
                    label: const Text(
                      'CONFIRMAR ENTRADA MANUAL',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                  ),
                ),
              ] else ...[
                const SizedBox(height: 8),
                Text(
                  _formatarDataHora(convidado.dataHoraEntrada) ?? 'Já deu entrada anteriormente.',
                  style: const TextStyle(color: Colors.black87, fontSize: 13, fontWeight: FontWeight.w600),
                ),
              ],
              if (_erroConfirmacao != null) ...[
                const SizedBox(height: 8),
                Text(
                  _erroConfirmacao!,
                  style: const TextStyle(color: Colors.red, fontSize: 13),
                ),
              ],
            ],
          ),
        ),
        Positioned(
          top: -20,
          left: 0,
          right: 0,
          child: Align(
            alignment: Alignment.topCenter,
            child: ConfettiWidget(
              confettiController: _confettiController,
              blastDirectionality: BlastDirectionality.explosive,
              shouldLoop: false,
              numberOfParticles: 30,
              gravity: 0.3,
              colors: const [Colors.amber, Colors.white, Colors.black87],
            ),
          ),
        ),
      ],
    );
  }
}
