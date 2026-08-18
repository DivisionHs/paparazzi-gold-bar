import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/guest_model.dart';
import '../models/aniversariante_model.dart';
import '../models/validacao_qr_model.dart';

// Exceção genérica para falhas de comunicação com a API.
// A mensagem já vem pronta para ser exibida direto na tela (SnackBar/alerta).
class ApiException implements Exception {
  final String mensagem;
  ApiException(this.mensagem);

  @override
  String toString() => mensagem;
}

// Lançada quando o token do aniversariante não existe ou a lista já foi encerrada (404).
class AniversarianteNaoEncontradoException extends ApiException {
  AniversarianteNaoEncontradoException()
      : super('Lista de aniversário não encontrada ou encerrada.');
}

// Lançada quando o backend recusa o cadastro por CPF duplicado nesta lista (400).
class CpfDuplicadoException extends ApiException {
  CpfDuplicadoException(super.mensagem);
}

// Lançada quando uma rota staff-only responde 401 — a sessão do funcionário
// expirou ou é inválida. A tela que capturar isso deve levar de volta ao
// login (ver staff_gate.dart), não só mostrar a mensagem genérica.
class NaoAutorizadoException extends ApiException {
  NaoAutorizadoException()
      : super('Sua sessão expirou. Faça login novamente.');
}

class ApiService {
  // URL base da API. Parametrizada via `--dart-define=API_URL=https://sua-api.com`
  // no build/run. Sem a flag, cai no fallback local de desenvolvimento.
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  // Header de autenticação pras rotas staff-only (Portaria, painel do dia).
  // O token vem da sessão ativa do Supabase Auth (login feito em
  // LoginScreen) — se não houver sessão, a chamada segue sem o header e o
  // backend recusa com 401 (tratado em _tratarRespostaProtegida).
  Map<String, String> get _headersAutenticados {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // Handshake inicial: busca nome e foto do aniversariante a partir do token da URL.
  Future<Aniversariante> buscarAniversariante(String token) async {
    final Uri url = Uri.parse('$baseUrl/aniversariantes/validar-token/$token');

    http.Response response;
    try {
      response = await http.get(url);
    } catch (_) {
      throw ApiException('Não foi possível conectar ao servidor.');
    }

    if (response.statusCode == 200) {
      return Aniversariante.fromJson(jsonDecode(response.body));
    }

    if (response.statusCode == 404) {
      throw AniversarianteNaoEncontradoException();
    }

    throw ApiException('Não foi possível carregar os dados do aniversariante.');
  }

  // Envia o cadastro do convidado e retorna o token de QR Code em caso de sucesso.
  Future<ConfirmacaoResultado> confirmarPresenca(Guest guest, String leadId) async {
    final Uri url = Uri.parse('$baseUrl/convidados/confirmar');

    http.Response response;
    try {
      response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(guest.toApiJson(leadId)),
      );
    } catch (_) {
      throw ApiException('Não foi possível conectar ao servidor.');
    }

    if (response.statusCode == 200 || response.statusCode == 201) {
      return ConfirmacaoResultado.fromJson(jsonDecode(response.body));
    }

    String mensagemErro = 'Erro ao confirmar presença.';
    try {
      final corpoErro = jsonDecode(response.body);
      mensagemErro = corpoErro['detail']?.toString() ?? mensagemErro;
    } catch (_) {
      // Corpo da resposta não veio em JSON — mantém a mensagem genérica.
    }

    if (response.statusCode == 400) {
      throw CpfDuplicadoException(mensagemErro);
    }

    throw ApiException(mensagemErro);
  }

  // Chamado pelo app da portaria a cada QR Code bipado. O backend sempre
  // responde HTTP 200 — quem diz se a entrada foi liberada é o campo "status".
  Future<ValidacaoQrResultado> validarQrCode(String qrCodeToken) async {
    final Uri url = Uri.parse('$baseUrl/convidados/validar-qr');

    http.Response response;
    try {
      response = await http.post(
        url,
        headers: _headersAutenticados,
        body: jsonEncode({'qr_code_token': qrCodeToken}),
      );
    } catch (_) {
      throw ApiException('Não foi possível conectar ao servidor.');
    }

    if (response.statusCode == 401) {
      throw NaoAutorizadoException();
    }

    if (response.statusCode != 200) {
      throw ApiException('Erro ao validar o QR Code (HTTP ${response.statusCode}).');
    }

    return ValidacaoQrResultado.fromJson(jsonDecode(response.body));
  }

  // Busca manual de contingência por CPF, usada quando o convidado chega sem
  // o QR Code em mãos (ver docs/visao_geral_paparazzi.md, seção 4).
  Future<ConvidadoEncontrado> buscarConvidadoPorCpf(String cpf) async {
    final Uri url = Uri.parse('$baseUrl/convidados/buscar-cpf/$cpf');

    http.Response response;
    try {
      response = await http.get(url, headers: _headersAutenticados);
    } catch (_) {
      throw ApiException('Não foi possível conectar ao servidor.');
    }

    if (response.statusCode == 200) {
      return ConvidadoEncontrado.fromJson(jsonDecode(response.body));
    }

    if (response.statusCode == 401) {
      throw NaoAutorizadoException();
    }

    String mensagemErro = 'Não foi possível concluir a busca manual.';
    try {
      final corpoErro = jsonDecode(response.body);
      mensagemErro = corpoErro['detail']?.toString() ?? mensagemErro;
    } catch (_) {
      // Corpo da resposta não veio em JSON — mantém a mensagem genérica.
    }

    throw ApiException(mensagemErro);
  }

  // Painel do dia (staff-only): aniversariantes com reserva para hoje, com
  // horário/estimativa e a quantidade real de convidados já confirmados.
  Future<List<AniversarianteHoje>> buscarAniversariantesHoje() async {
    final Uri url = Uri.parse('$baseUrl/aniversariantes/hoje');

    http.Response response;
    try {
      response = await http.get(url, headers: _headersAutenticados);
    } catch (_) {
      throw ApiException('Não foi possível conectar ao servidor.');
    }

    if (response.statusCode == 401) {
      throw NaoAutorizadoException();
    }

    if (response.statusCode != 200) {
      throw ApiException('Não foi possível carregar os aniversariantes do dia.');
    }

    final corpo = jsonDecode(response.body) as Map<String, dynamic>;
    final lista = corpo['aniversariantes'] as List<dynamic>? ?? [];
    return lista
        .map((item) => AniversarianteHoje.fromJson(item as Map<String, dynamic>))
        .toList();
  }
}
