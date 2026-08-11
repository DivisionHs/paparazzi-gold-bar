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
