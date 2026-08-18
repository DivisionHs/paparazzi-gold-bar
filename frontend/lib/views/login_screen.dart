import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

// Login de funcionário (Supabase Auth, e-mail/senha). Contas são criadas
// manualmente no dashboard do Supabase (Authentication > Users) — não há
// tela de self-signup nesta versão. Ao logar com sucesso, staff_gate.dart
// reage à mudança de sessão e troca esta tela pelo HubScreen sozinho.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _senhaController = TextEditingController();

  bool _autenticando = false;
  String? _erro;

  static const Color colorNight = Color(0xFF090909);
  static const Color colorGraphite = Color(0xFF1F1F1F);
  static const Color colorGold = Color(0xFFD4A94F);
  static const Color colorSoftGold = Color(0xFFF1D38E);

  @override
  void dispose() {
    _emailController.dispose();
    _senhaController.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _autenticando = true;
      _erro = null;
    });

    try {
      await Supabase.instance.client.auth.signInWithPassword(
        email: _emailController.text.trim(),
        password: _senhaController.text,
      );
      // Sucesso: staff_gate.dart escuta onAuthStateChange e troca de tela
      // sozinho — nada a fazer aqui além de limpar o estado de carregamento.
    } on AuthException catch (e) {
      setState(() => _erro = e.message.contains('Invalid login credentials')
          ? 'E-mail ou senha incorretos.'
          : e.message);
    } catch (_) {
      setState(() => _erro = 'Não foi possível conectar ao servidor de login.');
    } finally {
      if (mounted) setState(() => _autenticando = false);
    }
  }

  InputDecoration _inputDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: colorSoftGold, fontSize: 14),
      filled: true,
      fillColor: colorGraphite.withOpacity(0.8),
      prefixIcon: Icon(icon, color: colorGold),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.white10),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: colorGold, width: 1.5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF161616), colorNight, Color(0xFF0D0D0D)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24.0),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: colorGold.withOpacity(0.3)),
                    boxShadow: [
                      BoxShadow(color: colorGold.withOpacity(0.08), blurRadius: 30, spreadRadius: 2),
                    ],
                  ),
                  padding: const EdgeInsets.all(24.0),
                  child: Form(
                    key: _formKey,
                    child: Column(
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
                        Container(height: 1, width: 48, color: colorGold.withOpacity(0.5)),
                        const SizedBox(height: 8),
                        const Text(
                          'Acesso da Equipe',
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                        const SizedBox(height: 32),
                        TextFormField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          style: const TextStyle(color: Colors.white),
                          decoration: _inputDecoration('E-mail', Icons.person_outline),
                          validator: (v) => (v == null || v.trim().isEmpty) ? 'Digite seu e-mail' : null,
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _senhaController,
                          obscureText: true,
                          style: const TextStyle(color: Colors.white),
                          decoration: _inputDecoration('Senha', Icons.lock_outline),
                          validator: (v) => (v == null || v.isEmpty) ? 'Digite sua senha' : null,
                          onFieldSubmitted: (_) => _entrar(),
                        ),
                        if (_erro != null) ...[
                          const SizedBox(height: 16),
                          Text(_erro!, style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
                        ],
                        const SizedBox(height: 28),
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: ElevatedButton(
                            onPressed: _autenticando ? null : _entrar,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: colorGold,
                              foregroundColor: colorNight,
                              disabledBackgroundColor: colorGold.withOpacity(0.4),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              elevation: 0,
                            ),
                            child: _autenticando
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: colorNight),
                                  )
                                : const Text(
                                    'ENTRAR',
                                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
