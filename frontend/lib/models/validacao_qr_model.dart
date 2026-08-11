// Retorno do backend ao bipar o QR Code na portaria (POST /convidados/validar-qr).
// O status "LIBERADO"/"JA_UTILIZADO"/"INVALIDO" é quem manda no estado da tela,
// não o código HTTP: o endpoint sempre responde 200 para não travar a leitura.
class ValidacaoQrResultado {
  final String status;
  final String? mensagem;
  final String? nomeCompleto; // presente quando status == LIBERADO ou JA_UTILIZADO
  final String? cpf;
  final String? dataHoraEntrada; // presente em LIBERADO e JA_UTILIZADO

  // Dados do aniversariante responsável pela lista (join com kommo_lead_id).
  // eAniversariante só é true quando o CPF do próprio convidado lido bate
  // com o CPF cadastrado do aniversariante daquela lista.
  final bool eAniversariante;
  final String? nomeAniversariante;
  final String? cpfAniversariante;

  ValidacaoQrResultado({
    required this.status,
    this.mensagem,
    this.nomeCompleto,
    this.cpf,
    this.dataHoraEntrada,
    this.eAniversariante = false,
    this.nomeAniversariante,
    this.cpfAniversariante,
  });

  factory ValidacaoQrResultado.fromJson(Map<String, dynamic> json) {
    final convidado = json['convidado'] as Map<String, dynamic>?;
    final aniversariante = json['aniversariante'] as Map<String, dynamic>?;
    return ValidacaoQrResultado(
      status: json['status']?.toString() ?? 'INVALIDO',
      mensagem: json['mensagem']?.toString(),
      nomeCompleto: convidado?['nome_completo']?.toString(),
      cpf: convidado?['cpf']?.toString(),
      dataHoraEntrada: json['data_hora_entrada']?.toString(),
      eAniversariante: json['e_aniversariante'] == true,
      nomeAniversariante: aniversariante?['nome_completo']?.toString(),
      cpfAniversariante: aniversariante?['cpf']?.toString(),
    );
  }
}

// Resultado da busca manual por CPF (contingência quando o convidado não tem
// o QR Code em mãos). Reflete uma linha da tabela `convidados`, já com o
// aniversariante da lista embutido pelo mesmo join usado em validar-qr.
class ConvidadoEncontrado {
  final String nomeCompleto;
  final String cpf;
  final String qrCodeToken; // usado para liberar a entrada manualmente via validarQrCode
  final bool utilizado;
  final String? dataHoraEntrada;

  final bool eAniversariante;
  final String? nomeAniversariante;
  final String? cpfAniversariante;

  ConvidadoEncontrado({
    required this.nomeCompleto,
    required this.cpf,
    required this.qrCodeToken,
    required this.utilizado,
    this.dataHoraEntrada,
    this.eAniversariante = false,
    this.nomeAniversariante,
    this.cpfAniversariante,
  });

  factory ConvidadoEncontrado.fromJson(Map<String, dynamic> json) {
    final aniversariante = json['aniversariante'] as Map<String, dynamic>?;
    return ConvidadoEncontrado(
      nomeCompleto: json['nome_completo']?.toString() ?? '',
      cpf: json['cpf']?.toString() ?? '',
      qrCodeToken: json['qr_code_token']?.toString() ?? '',
      utilizado: json['utilizado'] == true,
      dataHoraEntrada: json['data_hora_entrada']?.toString(),
      eAniversariante: json['e_aniversariante'] == true,
      nomeAniversariante: aniversariante?['nome_completo']?.toString(),
      cpfAniversariante: aniversariante?['cpf']?.toString(),
    );
  }
}
