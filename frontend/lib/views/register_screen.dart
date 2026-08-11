import 'package:flutter/material.dart';
import 'package:mask_text_input_formatter/mask_text_input_formatter.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../models/guest_model.dart';
import '../models/aniversariante_model.dart';
import '../services/api_service.dart';

// Estados possíveis da tela, do handshake do token até o passaporte de QR Code.
enum _EstadoTela { carregando, erroToken, formulario, sucesso }

class RegisterScreen extends StatefulWidget {
  // Token exclusivo do aniversariante, lido da URL (?token=<UUID>) em main.dart.
  final String? token;

  const RegisterScreen({super.key, this.token});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _apiService = ApiService();

  final _nameController = TextEditingController();
  final _documentController = TextEditingController();
  final _birthdayController = TextEditingController();
  final _phoneController = TextEditingController();

  _EstadoTela _estadoTela = _EstadoTela.carregando;
  Aniversariante? _aniversariante;
  String? _qrCodeToken;
  bool _isSubmitting = false;

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);
  static const Color colorSoftGold = Color(0xFFF1D38E);

  final _birthdayFormatter = MaskTextInputFormatter(
    mask: '##/##/####',
    filter: {"#": RegExp(r'[0-9]')},
  );

  final _phoneFormatter = MaskTextInputFormatter(
    mask: '(##) #####-####',
    filter: {"#": RegExp(r'[0-9]')},
  );

  final _documentFormatter = MaskTextInputFormatter(
    mask: '###.###.###-##',
    filter: {"#": RegExp(r'[0-9]')},
  );

  @override
  void initState() {
    super.initState();
    _carregarAniversariante();
  }

  // Handshake inicial: valida o token da URL e carrega nome/foto do aniversariante.
  Future<void> _carregarAniversariante() async {
    final token = widget.token;

    if (token == null || token.isEmpty) {
      setState(() => _estadoTela = _EstadoTela.erroToken);
      return;
    }

    try {
      final aniversariante = await _apiService.buscarAniversariante(token);
      if (!mounted) return;
      setState(() {
        _aniversariante = aniversariante;
        _estadoTela = _EstadoTela.formulario;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _estadoTela = _EstadoTela.erroToken);
    }
  }

  bool _isValidCPF(String cpf) {
    final numericoCpf = cpf.replaceAll(RegExp(r'\D'), '');
    if (numericoCpf.length != 11) return false;
    if (RegExp(r'^(\d)\1+$').hasMatch(numericoCpf)) return false;

    int soma = 0;
    for (int i = 0; i < 9; i++) {
      soma += int.parse(numericoCpf[i]) * (10 - i);
    }
    int resto = soma % 11;
    int digito1 = resto < 2 ? 0 : 11 - resto;
    if (int.parse(numericoCpf[9]) != digito1) return false;

    soma = 0;
    for (int i = 0; i < 10; i++) {
      soma += int.parse(numericoCpf[i]) * (11 - i);
    }
    resto = soma % 11;
    int digito2 = resto < 2 ? 0 : 11 - resto;
    if (int.parse(numericoCpf[10]) != digito2) return false;

    return true;
  }

  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      locale: const Locale('pt', 'BR'),
      initialDate: DateTime(2000),
      firstDate: DateTime(1920),
      lastDate: DateTime.now(),
      builder: (context, child) {
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

    if (!mounted || picked == null) return;

    final day = picked.day.toString().padLeft(2, '0');
    final month = picked.month.toString().padLeft(2, '0');
    final year = picked.year.toString();

    setState(() {
      _birthdayController.text = '$day/$month/$year';
    });
  }

  Future<void> _submitForm() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_aniversariante == null) return;

    try {
      setState(() => _isSubmitting = true);

      final novoConvidado = Guest(
        name: _nameController.text,
        document: _documentController.text,
        phone: _phoneController.text,
        birthday: _birthdayController.text,
      );

      final resultado = await _apiService.confirmarPresenca(
        novoConvidado,
        _aniversariante!.leadId,
      );

      if (!mounted) return;

      setState(() {
        _isSubmitting = false;
        _qrCodeToken = resultado.qrCodeToken;
        _estadoTela = _EstadoTela.sucesso;
      });
    } catch (erro) {
      if (!mounted) return;

      setState(() => _isSubmitting = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(erro.toString()),
          backgroundColor: Colors.amber[800],
        ),
      );
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _documentController.dispose();
    _birthdayController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  InputDecoration _inputDecoration(
    String label,
    IconData icon, {
    String? hintText,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: colorSoftGold, fontSize: 14),
      hintText: hintText,
      hintStyle: const TextStyle(color: Colors.white30, fontSize: 14),
      filled: true,
      fillColor: colorGraphite.withOpacity(0.8),
      prefixIcon: Icon(icon, color: colorGold),
      suffixIcon: suffixIcon,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.white10),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: colorGold, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.redAccent.withOpacity(0.5)),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.redAccent, width: 1.5),
      ),
    );
  }

  // Banner com o nome e a foto do aniversariante, vindos do handshake do token.
  // Prioriza a foto original (fotoPerfilUrl) — o flyer completo (fotoUrl) não
  // fica bom recortado num avatar circular; fica como fallback só para
  // cadastros antigos que não tenham foto_perfil_url salva no Supabase.
  Widget _buildAniversarianteSection() {
    final aniversariante = _aniversariante!;
    final nomeAniversariante = aniversariante.nomeCompleto;
    final urlFoto = aniversariante.fotoPerfilUrl ?? aniversariante.fotoUrl;

    return Column(
      children: [
        Stack(
          alignment: Alignment.bottomCenter,
          clipBehavior: Clip.none,
          children: [
            Container(
              width: 160,
              height: 160,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: colorGold.withOpacity(0.6), width: 3),
                boxShadow: [
                  BoxShadow(
                    color: colorGold.withOpacity(0.3),
                    blurRadius: 20,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(80),
                child: (urlFoto != null && urlFoto.isNotEmpty)
                    ? Image.network(
                        urlFoto,
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) {
                          return Container(
                            color: colorGraphite,
                            child: const Icon(Icons.person, color: colorGold, size: 50),
                          );
                        },
                      )
                    : Container(
                        color: colorGraphite,
                        child: const Icon(Icons.person, color: colorGold, size: 50),
                      ),
              ),
            ),
            Positioned(
              bottom: -10,
              child: Container(
                decoration: BoxDecoration(
                  color: colorGold,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.3),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                child: const Text(
                  'HOST VIP',
                  style: TextStyle(
                    color: colorNight,
                    fontWeight: FontWeight.bold,
                    fontSize: 10,
                    letterSpacing: 1.5,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        RichText(
          textAlign: TextAlign.center,
          text: TextSpan(
            style: const TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
            children: [
              const TextSpan(text: 'Aniversário do '),
              TextSpan(
                text: nomeAniversariante,
                style: const TextStyle(
                  color: colorGold,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16.0),
          child: Text(
            'Você foi convidado para comemorar esta data exclusiva conosco! Confirme seus dados para entrar na lista oficial.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.4),
          ),
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: Divider(color: Colors.white.withOpacity(0.1), thickness: 1),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.0),
              child: Text(
                'CONFIRMAÇÃO DE PRESENÇA',
                style: TextStyle(
                  color: colorGold,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.5,
                ),
              ),
            ),
            Expanded(
              child: Divider(color: Colors.white.withOpacity(0.1), thickness: 1),
            ),
          ],
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  // Moldura visual (fundo, cartão dourado, largura máxima mobile-first) compartilhada
  // por todos os estados da tela: carregando, erro, formulário e passaporte VIP.
  Widget _buildMoldura({required Widget child}) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF161616),
              colorNight,
              Color(0xFF0D0D0D),
            ],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 500),
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: colorGold.withOpacity(0.3)),
                    boxShadow: [
                      BoxShadow(
                        color: colorGold.withOpacity(0.08),
                        blurRadius: 30,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  padding: const EdgeInsets.all(24.0),
                  child: child,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCabecalhoMarca() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'PAPARAZZI GOLD BAR',
          style: TextStyle(
            color: colorSoftGold,
            fontSize: 12,
            fontWeight: FontWeight.w300,
            letterSpacing: 4.0,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          height: 1,
          width: 48,
          color: colorGold.withOpacity(0.5),
        ),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildCarregando() {
    return _buildMoldura(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildCabecalhoMarca(),
          const CircularProgressIndicator(color: colorGold),
          const SizedBox(height: 16),
          const Text(
            'Carregando lista de aniversário...',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white70, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildErroToken() {
    return _buildMoldura(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildCabecalhoMarca(),
          const Icon(Icons.link_off, color: colorGold, size: 56),
          const SizedBox(height: 16),
          const Text(
            'Lista de aniversário não encontrada ou encerrada.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Verifique se o link recebido está completo e tente novamente.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white60, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildFormulario() {
    return _buildMoldura(
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildCabecalhoMarca(),
            _buildAniversarianteSection(),
            TextFormField(
              controller: _nameController,
              style: const TextStyle(color: Colors.white),
              decoration: _inputDecoration(
                'Nome Completo',
                Icons.person,
                hintText: 'Digite seu nome completo',
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Por favor, digite o nome completo';
                }
                if (value.trim().split(' ').length < 2) {
                  return 'Por favor, digite seu nome e sobrenome.';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _documentController,
              inputFormatters: [_documentFormatter],
              keyboardType: TextInputType.number,
              style: const TextStyle(color: Colors.white),
              decoration: _inputDecoration(
                'CPF',
                Icons.badge,
                hintText: '000.000.000-00',
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Por favor, insira o seu CPF.';
                }
                if (!_isValidCPF(value)) {
                  return 'CPF inválido. Verifique os números digitados.';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _phoneController,
              inputFormatters: [_phoneFormatter],
              keyboardType: TextInputType.phone,
              style: const TextStyle(color: Colors.white),
              decoration: _inputDecoration(
                'WhatsApp',
                Icons.phone,
                hintText: '(00) 00000-0000',
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Por favor, digite o celular';
                }
                final digits = value.replaceAll(RegExp(r'\D'), '').length;
                if (digits < 10 || digits > 11) {
                  return 'Certifique-se de incluir o DDD correto.';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _birthdayController,
              inputFormatters: [_birthdayFormatter],
              keyboardType: TextInputType.number,
              readOnly: true,
              onTap: () => _selectDate(context),
              style: const TextStyle(color: Colors.white),
              decoration: _inputDecoration(
                'Data de Nascimento',
                Icons.calendar_today,
                hintText: 'DD/MM/AAAA',
                suffixIcon: IconButton(
                  icon: const Icon(Icons.date_range, color: colorGold),
                  onPressed: () => _selectDate(context),
                ),
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return 'Por favor, selecione a data de nascimento';
                }
                return null;
              },
            ),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: _isSubmitting ? null : _submitForm,
                style: ElevatedButton.styleFrom(
                  backgroundColor: colorGold,
                  foregroundColor: colorNight,
                  disabledBackgroundColor: colorGold.withOpacity(0.4),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 0,
                ),
                child: _isSubmitting
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: colorNight,
                        ),
                      )
                    : const Text(
                        'CONFIRMAR PRESENÇA NA LISTA',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 0.5,
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Passaporte VIP: tela final exibida após a confirmação de presença, com o
  // QR Code individual do convidado (qr_code_token real vindo do backend).
  Widget _buildPassaporteVip() {
    final nomeConvidado = _nameController.text;

    return _buildMoldura(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.check_circle_outline,
            color: colorGold,
            size: 60,
          ),
          const SizedBox(height: 16),
          const Text(
            'Presença Confirmada!',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white,
              fontSize: 22,
              fontWeight: FontWeight.bold,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Tudo pronto, $nomeConvidado! Este é o seu passaporte VIP para a Paparazzi Gold Bar.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.grey[400],
              fontSize: 14,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: colorGold.withOpacity(0.2),
                  blurRadius: 15,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: SizedBox(
              width: 180,
              height: 180,
              child: QrImageView(
                data: _qrCodeToken ?? '',
                version: QrVersions.auto,
                size: 180.0,
                gapless: false,
              ),
            ),
          ),
          const SizedBox(height: 20),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: colorGold.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: colorGold.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.camera_alt_outlined, color: colorGold, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Tire um print desta tela e apresente na portaria para agilizar sua entrada.',
                    style: TextStyle(color: Colors.grey[300], fontSize: 12, height: 1.3),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    switch (_estadoTela) {
      case _EstadoTela.carregando:
        return _buildCarregando();
      case _EstadoTela.erroToken:
        return _buildErroToken();
      case _EstadoTela.formulario:
        return _buildFormulario();
      case _EstadoTela.sucesso:
        return _buildPassaporteVip();
    }
  }
}
