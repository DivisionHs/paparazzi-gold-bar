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
      horarioReserva: json['horario_reserva']?.toString(),
      estimativaConvidados: json['estimativa_convidados'] as int?,
      quantidadeConfirmada: json['quantidade_confirmada'] as int? ?? 0,
    );
  }
}
