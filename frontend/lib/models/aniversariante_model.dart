// O Postgres devolve colunas TIME como "HH:MM:SS" (ex.: "19:00:00"), mesmo
// quando o backend gravou só "HH:MM" -- corta os segundos pra exibição,
// sem quebrar se o valor já vier curto ou em outro formato inesperado.
String? _formatarHoraCurta(String? valor) {
  if (valor == null || valor.isEmpty) return null;
  return valor.length >= 5 ? valor.substring(0, 5) : valor;
}

// Dados do aniversariante retornados pelo handshake de token, feito em
// GET /aniversariantes/validar-token/{token} assim que a tela é aberta.
class Aniversariante {
  final String leadId; // Identificador usado para vincular o convidado à lista correta
  final String nomeCompleto;
  final String? fotoUrl; // Flyer composto (foto + moldura + nome)
  final String? fotoPerfilUrl; // Foto original enviada pelo aniversariante, sem composição

  Aniversariante({
    required this.leadId,
    required this.nomeCompleto,
    this.fotoUrl,
    this.fotoPerfilUrl,
  });

  factory Aniversariante.fromJson(Map<String, dynamic> json) {
    return Aniversariante(
      leadId: json['lead_id'].toString(),
      nomeCompleto: json['nome_completo']?.toString() ?? 'Aniversariante',
      fotoUrl: json['foto_url']?.toString(),
      fotoPerfilUrl: json['foto_perfil_url']?.toString(),
    );
  }
}

// Retorno do backend após a confirmação de presença ser aceita (HTTP 201).
class ConfirmacaoResultado {
  final String qrCodeToken;

  ConfirmacaoResultado({required this.qrCodeToken});

  factory ConfirmacaoResultado.fromJson(Map<String, dynamic> json) {
    return ConfirmacaoResultado(qrCodeToken: json['qr_code_token'].toString());
  }
}

// Uma linha do painel de aniversariantes do dia (GET /aniversariantes/hoje,
// rota staff-only). horarioReserva/estimativaConvidados vêm do Kommo,
// persistidos desde a migration 20260817_01; quantidadeConfirmada é sempre
// contada ao vivo na tabela `convidados`.
class AniversarianteHoje {
  final String leadId;
  final String nomeCompleto;
  final String? horarioReserva;
  final int? estimativaConvidados;
  final int quantidadeConfirmada;

  AniversarianteHoje({
    required this.leadId,
    required this.nomeCompleto,
    this.horarioReserva,
    this.estimativaConvidados,
    required this.quantidadeConfirmada,
  });

  factory AniversarianteHoje.fromJson(Map<String, dynamic> json) {
    return AniversarianteHoje(
      leadId: json['lead_id'].toString(),
      nomeCompleto: json['nome_completo']?.toString() ?? 'Aniversariante',
      horarioReserva: _formatarHoraCurta(json['horario_reserva']?.toString()),
      estimativaConvidados: json['estimativa_convidados'] as int?,
      quantidadeConfirmada: json['quantidade_confirmada'] as int? ?? 0,
    );
  }
}

// Uma linha da lista de convidados de um aniversariante (GET
// /convidados/lista/{lead_id}, rota staff-only), aberta ao tocar no nome do
// aniversariante no painel do dia. `utilizado` é a mesma coluna marcada por
// POST /convidados/validar-qr na Portaria -- true quando o convidado já
// bipou entrada de verdade, não só confirmou presença no formulário.
class ConvidadoResumo {
  final String id;
  final String nomeCompleto;
  final String? whatsapp;
  final bool utilizado;

  ConvidadoResumo({required this.id, required this.nomeCompleto, this.whatsapp, this.utilizado = false});

  factory ConvidadoResumo.fromJson(Map<String, dynamic> json) {
    return ConvidadoResumo(
      id: json['id'].toString(),
      nomeCompleto: json['nome_completo']?.toString() ?? 'Convidado',
      whatsapp: json['whatsapp']?.toString(),
      utilizado: json['utilizado'] == true,
    );
  }

  // Cópia com `utilizado` alterado -- usada pra atualizar a lista na tela
  // (ConvidadosListaScreen) sem precisar recarregar tudo do backend depois
  // de confirmar/desfazer uma entrada manual.
  ConvidadoResumo copyWith({bool? utilizado}) {
    return ConvidadoResumo(
      id: id,
      nomeCompleto: nomeCompleto,
      whatsapp: whatsapp,
      utilizado: utilizado ?? this.utilizado,
    );
  }
}
