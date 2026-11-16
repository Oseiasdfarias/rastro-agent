from rootcause.domain.models import FailureMode

MATERIALS = [
    ("MAT-1001", "Junta de vedação 40 mm"),
    ("MAT-1002", "Junta de vedação 65 mm"),
    ("MAT-1003", "Coxim antivibração 80 mm"),
    ("MAT-1004", "Coxim antivibração 120 mm"),
    ("MAT-1005", "Anel O-ring NBR 25 mm"),
    ("MAT-1006", "Bucha de suspensão industrial"),
    ("MAT-1007", "Perfil de vedação porta 18 mm"),
    ("MAT-1008", "Perfil de vedação janela 12 mm"),
    ("MAT-1009", "Mangueira técnica 3/4 pol"),
    ("MAT-1010", "Mangueira técnica 1 pol"),
    ("MAT-1011", "Tira de borracha 3 mm"),
    ("MAT-1012", "Tira de borracha 5 mm"),
]

# Prensas moldam peças; extrusoras fazem perfis, mangueiras e tiras.
EQUIPMENT = [
    ("PR-01", "Prensa de moldagem 01", ["MAT-1001", "MAT-1002", "MAT-1005"]),
    ("PR-02", "Prensa de moldagem 02", ["MAT-1003", "MAT-1004"]),
    ("PR-03", "Prensa de moldagem 03", ["MAT-1005", "MAT-1006", "MAT-1001"]),
    ("PR-04", "Prensa de moldagem 04", ["MAT-1006", "MAT-1003"]),
    ("EX-01", "Extrusora 01", ["MAT-1007", "MAT-1008", "MAT-1011"]),
    ("EX-02", "Extrusora 02", ["MAT-1009", "MAT-1010", "MAT-1012"]),
]

MODES_BY_KIND = {
    "PR": [
        FailureMode.bearing_wear,
        FailureMode.heater_drift,
        FailureMode.mold_wear,
        FailureMode.sensor_fault,
    ],
    "EX": [
        FailureMode.bearing_wear,
        FailureMode.heater_drift,
        FailureMode.misalignment,
        FailureMode.sensor_fault,
    ],
}

# Notas do turno dentro da janela de falha: começam vagas, ficam mais claras.
SYMPTOM_NOTES = {
    FailureMode.bearing_wear: [
        "ruido anormal lado acion., operador relata",
        "vibr. acima do normal no mancal, verificar",
        "mancal aquecendo, cheiro de graxa queimada",
        "ruido metalico continuo no mancal do acion.",
    ],
    FailureMode.heater_drift: [
        "temp. placa sup oscilando durante ciclo",
        "ciclo de cura demorando mais q o normal",
        "termopar ok, resistencia placa sup c/ leitura instavel",
        "temp. placa abaixo do set em 8 a 12 graus",
    ],
    FailureMode.mold_wear: [
        "rebarba aumentando na cavidade 3",
        "operador fazendo rebarbação manual extra",
        "linha de fechamento do molde gasta, verif.",
        "desgaste visivel na cavidade, dimensao no limite",
    ],
    FailureMode.misalignment: [
        "perfil saindo levemente torto, ajustado puxador",
        "espessura variando entre lados do perfil",
        "matriz desalinhada? conferir fixação",
        "puxador forçando de um lado, desalinhamento",
    ],
    FailureMode.sensor_fault: [
        "sensor pressão c/ leitura pulando",
        "alarme falso de pressão 2x no turno",
        "sinal do transdutor de pressão intermitente",
        "pressão registrada não bate c/ manômetro",
    ],
}

REPAIRS = {
    FailureMode.bearing_wear: "Troca do rolamento do mancal lado acionamento",
    FailureMode.heater_drift: "Troca da resistência da placa superior e recalibração",
    FailureMode.mold_wear: "Retífica do molde e troca de inserto da cavidade 3",
    FailureMode.misalignment: "Realinhamento da matriz e do puxador",
    FailureMode.sensor_fault: "Troca do transdutor de pressão",
}

ROUTINE_NOTES = [
    "limpeza do molde fim de turno",
    "ajuste de setup p/ troca de produto",
    "inspeção visual ok, sem anomalias",
    "reaperto de parafusos da proteção",
    "troca de filtro do sistema hidraulico (programada)",
]

ROUTINE_ORDER = "Lubrificação geral e inspeção preventiva"

COMPLAINT_TEXTS = {
    FailureMode.bearing_wear: [
        "Peças com marcas onduladas na superfície e espessura irregular.",
        "Recebemos peças com variação de dimensão, algumas fora da tolerância.",
    ],
    FailureMode.heater_drift: [
        "Borracha mole e pegajosa, parece que não curou direito.",
        "Peças com bolhas internas e dureza abaixo do especificado.",
    ],
    FailureMode.mold_wear: [
        "Rebarba excessiva nas peças, nossa linha travou na montagem.",
        "Dimensão fora da tolerância e acabamento ruim na borda.",
    ],
    FailureMode.misalignment: [
        "Perfil chegou torto, não encaixa no trilho.",
        "Espessura diferente de um lado para o outro do perfil.",
    ],
    FailureMode.sensor_fault: [
        "Lote misturado: parte das peças boa, parte com dureza fora.",
        "Algumas peças rachando na instalação, outras normais.",
    ],
}

NOISE_TEXTS = [
    "Caixas chegaram molhadas e peças com manchas, transporte deixou exposto à chuva.",
    "Peças ressecadas; ficaram estocadas no pátio por meses antes do uso.",
    "Embalagem rasgada e peças amassadas na entrega.",
    "Usamos com óleo diferente do recomendado e a vedação inchou.",
    "Instalação com ferramenta errada cortou as peças.",
]
