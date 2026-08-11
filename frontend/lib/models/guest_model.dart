class Guest {
  final String name;
  final String document;    // CPF ou RG que o segurança vai ler
  final String phone;       // Número de celular/telefone
  final String birthday;    // Data de nascimento

  // Este é o construtor da classe. Ele obriga que, ao criar um novo convidado,
  // todas as informações (nome, documento e data) sejam fornecidas.
  Guest({
    required this.name,
    required this.document,
    required this.phone,
    required this.birthday,
  });

  // Monta o payload exatamente como o endpoint POST /convidados/confirmar espera,
  // já limpando máscaras (CPF/WhatsApp) e convertendo a data para o formato ISO.
  Map<String, dynamic> toApiJson(String leadId) {
    final cpfLimpo = document.replaceAll(RegExp(r'\D'), '');
    final whatsappLimpo = phone.replaceAll(RegExp(r'\D'), '');

    String dataFormatada = birthday;
    if (birthday.contains('/')) {
      final partes = birthday.split('/');
      if (partes.length == 3) {
        dataFormatada = "${partes[2]}-${partes[1]}-${partes[0]}";
      }
    }

    return {
      "lead_id": leadId,
      "nome_completo": name,
      "cpf": cpfLimpo,
      "whatsapp": whatsappLimpo,
      "data_nascimento": dataFormatada,
    };
  }
}
