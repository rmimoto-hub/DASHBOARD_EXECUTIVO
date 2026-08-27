"""Popula o banco com um ciclo completo do comite executivo.

Dados ficticios, mas coerentes por construcao: sao lancados apenas os
FATOS-BASE (valor por regional e por semana, com denominador quando o
indicador e taxa). Consolidado, acumulado, atingimento, semaforo e
projecao sao todos derivados pelo motor de KPI — nao existe numero
digitado duas vezes, entao nao ha como divergirem.

A historia embutida nos numeros e a mesma do comite: SP sustenta o
consolidado, RJ desvia moderado, RS quebra em quase tudo.

Uso:  make seed-comite
"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_senha  # noqa: E402
from app.models.cadastro import (  # noqa: E402
    Area,
    Ciclo,
    FonteDados,
    Indicador,
    MelhorDirecao,
    Regional,
    TipoAcumulacao,
    TipoFonte,
    Unidade,
)
from app.models.fatos import Detalhamento, Medicao, Meta  # noqa: E402
from app.models.nominal import (  # noqa: E402
    Cliente,
    Compromisso,
    NotaAnalitica,
    OcorrenciaEntrega,
    TituloInadimplente,
)
from app.models.usuario import Perfil, Usuario  # noqa: E402

ACUMULA, TAXA = TipoAcumulacao.ACUMULA, TipoAcumulacao.TAXA
MAIOR, MENOR = MelhorDirecao.MAIOR, MelhorDirecao.MENOR

SEMANAS = 4
SEMANA_CORRENTE = 3

USUARIOS = [
    ("Administrador", "admin@kamico.com.br", Perfil.ADMIN),
    ("Maria Silva", "maria@kamico.com.br", Perfil.USER),
    ("Joao Souza", "joao@kamico.com.br", Perfil.USER),
    ("Ana Costa", "ana@kamico.com.br", Perfil.READ_ONLY),
    ("Carlos Pereira", "carlos@kamico.com.br", Perfil.USER),
]

REGIONAIS = [("SP", "Sao Paulo", 1), ("RJ", "Rio de Janeiro", 2), ("RS", "Rio Grande do Sul", 3)]

# ---------------------------------------------------------------------
# Catalogo de indicadores
# (codigo, nome, area, unidade, tipo, direcao, rot_num, rot_den, ordem)
# ---------------------------------------------------------------------
INDICADORES = [
    ("FATURAMENTO", "Faturamento", Area.COMERCIAL, Unidade.BRL_MI, ACUMULA, MAIOR,
     None, None, 1),
    ("MARGEM_CONTRIB", "Margem de contribuicao", Area.COMERCIAL, Unidade.PCT, TAXA, MAIOR,
     "margem em R$", "faturamento", 2),
    ("BASE_ATIVA", "Base ativa de clientes", Area.COMERCIAL, Unidade.CLIENTES, TAXA, MAIOR,
     "clientes ativos", None, 3),
    ("POSITIVACAO", "Positivacao da base", Area.COMERCIAL, Unidade.CLIENTES, ACUMULA, MAIOR,
     None, None, 4),
    ("CONVERSAO_LEADS", "Conversao de leads em clientes", Area.COMERCIAL, Unidade.NUM, ACUMULA, MAIOR,
     None, None, 5),
    ("OTIF", "OTIF", Area.OPERACOES, Unidade.PCT, TAXA, MAIOR,
     "pedidos no prazo e completos", "pedidos entregues", 1),
    ("TEMPO_ENTREGA", "Tempo medio de entrega", Area.OPERACOES, Unidade.DIAS, TAXA, MENOR,
     "dias x pedidos", "pedidos entregues", 2),
    ("COBERTURA_ESTOQUE", "Cobertura de estoque", Area.ESTOQUE, Unidade.DIAS, TAXA, MENOR,
     "estoque a custo", "consumo medio diario", 1),
    ("OBSOLESCENCIA", "Estoque em obsolescencia", Area.ESTOQUE, Unidade.PCT, TAXA, MENOR,
     "estoque acima da meta de cobertura", "estoque total", 2),
    ("INADIMPLENCIA", "Taxa de inadimplencia", Area.FINANCEIRO, Unidade.PCT, TAXA, MENOR,
     "valor em aberto", "carteira", 1),
    ("RECUPERACAO", "Recuperacao de inadimplencia", Area.FINANCEIRO, Unidade.BRL_MIL, ACUMULA, MAIOR,
     None, None, 2),
    ("LEADS_QUALIFICADOS", "Leads qualificados", Area.MARKETING, Unidade.LEADS, ACUMULA, MAIOR,
     None, None, 1),
    ("CUSTO_POR_LEAD", "Custo por lead qualificado", Area.MARKETING, Unidade.BRL, TAXA, MENOR,
     "investimento", "leads qualificados", 2),
]

# Metas consolidadas do mes.
METAS = {
    "FATURAMENTO": "3.70", "MARGEM_CONTRIB": "0.340", "BASE_ATIVA": "448",
    "POSITIVACAO": "303", "CONVERSAO_LEADS": "27", "OTIF": "0.980",
    "TEMPO_ENTREGA": "1.9", "COBERTURA_ESTOQUE": "45", "OBSOLESCENCIA": "0.15",
    "INADIMPLENCIA": "0.040", "RECUPERACAO": "1100", "LEADS_QUALIFICADOS": "132",
    "CUSTO_POR_LEAD": "240",
}

# Metas por regional, para os indicadores que acumulam.
#
# Sem meta propria, o painel rateia a meta consolidada pelo peso do
# REALIZADO — o que faz todas as regionais exibirem o mesmo atingimento
# e apaga a quebra. Um comite de verdade define meta por regional, e e
# isso que permite ver que RS esta fora do ritmo e SP nao.
#
# Cada conjunto soma a meta consolidada correspondente.
METAS_REGIONAIS = {
    "FATURAMENTO":        {"SP": "1.60", "RJ": "1.15", "RS": "0.95"},
    "POSITIVACAO":        {"SP": "140",  "RJ": "90",   "RS": "73"},
    "CONVERSAO_LEADS":    {"SP": "12",   "RJ": "8",    "RS": "7"},
    "RECUPERACAO":        {"SP": "480",  "RJ": "350",  "RS": "270"},
    "LEADS_QUALIFICADOS": {"SP": "60",   "RJ": "40",   "RS": "32"},
    # Base ativa e TAXA para efeito de ritmo (esperado 100% em qualquer
    # semana), mas o valor e aditivo — logo tambem precisa de meta por
    # regional, senao RS seria cobrada dos 448 clientes da empresa.
    "BASE_ATIVA":         {"SP": "245",  "RJ": "120",  "RS": "83"},
}

# ---------------------------------------------------------------------
# Fatos-base.
#
# ACUMULA: valor de cada semana, por regional (o mes e a soma).
# TAXA:    (numerador, denominador) da posicao de cada semana.
#
# Construidos para SP sustentar, RJ desviar pouco e RS quebrar.
# ---------------------------------------------------------------------
FATOS_ACUMULA = {
    "FATURAMENTO": {  # R$ mi por semana
        "SP": ["0.42", "0.38", "0.37"],
        "RJ": ["0.28", "0.24", "0.24"],
        "RS": ["0.19", "0.16", "0.16"],
    },
    "POSITIVACAO": {  # clientes positivados por semana
        "SP": [46, 43, 41], "RJ": [24, 22, 21], "RS": [12, 11, 10],
    },
    "CONVERSAO_LEADS": {  # ganhos por semana
        "SP": [4, 5, 5], "RJ": [1, 3, 3], "RS": [1, 0, 1],
    },
    "RECUPERACAO": {  # R$ mil por semana
        "SP": [96, 92, 90], "RJ": [50, 46, 45], "RS": [30, 28, 29],
    },
    "LEADS_QUALIFICADOS": {  # leads por semana
        "SP": [19, 18, 20], "RJ": [10, 10, 10], "RS": [7, 7, 6],
    },
}

FATOS_TAXA = {
    "MARGEM_CONTRIB": {  # (margem R$ mi, faturamento R$ mi) acumulado
        "SP": [("0.147", "0.42"), ("0.280", "0.80"), ("0.412", "1.17")],
        "RJ": [("0.094", "0.28"), ("0.176", "0.52"), ("0.259", "0.76")],
        "RS": [("0.061", "0.19"), ("0.113", "0.35"), ("0.165", "0.51")],
    },
    "BASE_ATIVA": {  # clientes ativos no fim da semana
        "SP": [(214, None), (217, None), (220, None)],
        "RJ": [(108, None), (109, None), (110, None)],
        "RS": [(64, None), (64, None), (64, None)],
    },
    "OTIF": {  # (pedidos ok, pedidos entregues) acumulado
        "SP": [(228, 238), (462, 483), (706, 738)],
        "RJ": [(104, 114), (210, 230), (316, 347)],
        "RS": [(52, 63), (108, 131), (163, 199)],
    },
    "TEMPO_ENTREGA": {  # (dias x pedidos, pedidos) acumulado
        "SP": [("476", 238), ("966", 483), ("1476", 738)],
        "RJ": [("274", 114), ("552", 230), ("833", 347)],
        "RS": [("195", 63), ("406", 131), ("617", 199)],
    },
    "COBERTURA_ESTOQUE": {  # (estoque a custo R$ mil, consumo/dia R$ mil)
        "SP": [("2088", "36.0"), ("2070", "36.5"), ("2059", "35.5")],
        "RJ": [("1188", "16.5"), ("1200", "16.7"), ("1224", "17.0")],
        "RS": [("910", "8.8"), ("925", "8.9"), ("936", "9.0")],
    },
    "OBSOLESCENCIA": {  # (estoque obsoleto, estoque total) R$ mil
        "SP": [("452", "2088"), ("466", "2070"), ("474", "2059")],
        "RJ": [("392", "1188"), ("408", "1200"), ("416", "1224")],
        "RS": [("455", "910"), ("472", "925"), ("487", "936")],
    },
    "INADIMPLENCIA": {  # (valor em aberto, carteira) R$ mil
        "SP": [("430", "5620"), ("412", "5680"), ("398", "5740")],
        "RJ": [("268", "3180"), ("259", "3220"), ("251", "3260")],
        "RS": [("174", "1900"), ("168", "1930"), ("163", "1960")],
    },
    "CUSTO_POR_LEAD": {  # (investimento R$, leads qualificados) acumulado
        "SP": [("5263", 19), ("10249", 37), ("15789", 57)],
        "RJ": [("2970", 10), ("5940", 20), ("8910", 30)],
        "RS": [("2345", 7), ("4690", 14), ("6700", 20)],
    },
}

# ---------------------------------------------------------------------
# Detalhe nominal
# ---------------------------------------------------------------------
CLIENTES = [
    ("Salao Bella Hair Ltda", "RS", "Valmir Moreira"),
    ("Studio W JK Cosmeticos", "SP", "Raquel Brasil"),
    ("Rede Beleza Total", "SP", "Raquel Brasil"),
    ("Espaco Beleza Ipanema", "RJ", "Marcos Lima"),
    ("Hair Pro Canoas", "RS", "Valmir Moreira"),
    ("Beauty Center Moema", "SP", "Raquel Brasil"),
    ("Cabelos & Cia Niteroi", "RJ", "Marcos Lima"),
    ("Estudio Anita Hair", "RS", "Valmir Moreira"),
]

# (cliente, regional, causa, motivo, pedidos, plano, responsavel)
OCORRENCIAS = [
    ("Salao Bella Hair Ltda", "RS", "RUPTURA_ESTOQUE",
     "Ruptura de estoque na linha de tratamento", 6,
     "Antecipar transferencia do CD de SP", "Suprimentos"),
    ("Studio W JK Cosmeticos", "SP", "ATRASO_TRANSPORTE",
     "Atraso da transportadora", 5,
     "Reuniao de nivel de servico com o operador", "Logistica"),
    ("Espaco Beleza Ipanema", "RJ", "DIVERGENCIA_FISCAL",
     "Divergencia de nota fiscal", 4,
     "Revisao do cadastro fiscal do cliente", "Fiscal"),
    ("Hair Pro Canoas", "RS", "RUPTURA_ESTOQUE",
     "Ruptura de estoque na linha de coloracao", 4,
     "Reposicao emergencial via filial RS", "Suprimentos"),
    ("Beauty Center Moema", "SP", "SEPARACAO_INCOMPLETA",
     "Pedido incompleto na separacao", 3,
     "Dupla conferencia na expedicao do CD", "CD SP"),
    ("Outros 11 clientes", None, "DIVERSOS",
     "Motivos diversos e pontuais", 8,
     "Tratativa individual pelo consultor", "Comercial"),
]

# (cliente, R$ mil em aberto, dias de atraso, em negociacao)
TITULOS = [
    ("Salao Bella Hair Ltda", "118", 74, True),
    ("Studio W JK Cosmeticos", "104", 45, False),
    ("Rede Beleza Total", "92", 61, True),
    ("Espaco Beleza Ipanema", "81", 52, False),
    ("Hair Pro Canoas", "68", 88, True),
    ("Beauty Center Moema", "61", 38, False),
    ("Cabelos & Cia Niteroi", "55", 67, False),
    ("Estudio Anita Hair", "48", 95, True),
]

# Motivos das perdas de lead no mes (dimensao MOTIVO_PERDA).
MOTIVOS_PERDA = [
    ("Preco acima do concorrente", 14),
    ("Sem interesse no portfolio", 9),
    ("Condicao de pagamento / prazo", 7),
    ("Ja possui fornecedor exclusivo", 5),
    ("Pedido minimo muito alto", 4),
    ("Sem retorno apos contato", 2),
]

# Faixas de cobertura de estoque por regional (dimensao FAIXA_COBERTURA).
FAIXAS_COBERTURA = {
    "SP": [("Abaixo da meta (ruptura)", 14), ("Dentro da meta", 63),
           ("Acima da meta (obsolescencia)", 23)],
    "RJ": [("Abaixo da meta (ruptura)", 11), ("Dentro da meta", 55),
           ("Acima da meta (obsolescencia)", 34)],
    "RS": [("Abaixo da meta (ruptura)", 15), ("Dentro da meta", 33),
           ("Acima da meta (obsolescencia)", 52)],
}

# (frente, acao, responsavel, prazo, indicador, regional)
COMPROMISSOS = [
    ("RS · Faturamento", "Forca-tarefa de carteira com os 30 maiores clientes inativos",
     "Regional RS", date(2026, 8, 26), "FATURAMENTO", "RS"),
    ("RS · Inadimplencia", "Renegociacao dos 10 maiores titulos vencidos",
     "Financeiro + RS", date(2026, 8, 24), "INADIMPLENCIA", "RS"),
    ("Todos · Positivacao", "Campanha de pedido minimo para os clientes nao positivados",
     "Trade marketing", date(2026, 8, 22), "POSITIVACAO", None),
    ("Todos · Base ativa", "Plano de retencao: inativacoes superam as entradas",
     "Comercial", date(2026, 8, 28), "BASE_ATIVA", None),
    ("SP · Leads", "Redistribuicao de leads excedentes de SP para RS",
     "Marketing", date(2026, 8, 21), "LEADS_QUALIFICADOS", "SP"),
    ("Todos · Conversao", "Revisao da politica de preco para os leads em negociacao",
     "Comercial", date(2026, 8, 25), "CONVERSAO_LEADS", None),
]

# Leitura do comite por KPI (indicador ou None para o painel geral).
NOTAS = [
    (None, "SP sustenta o consolidado e mascara a quebra das outras "
           "regionais na media. A acao da semana 4 e sobre RS."),
    ("FATURAMENTO", "RS e a quebra principal. No ritmo atual o mes fecha "
                    "abaixo da meta; a semana 4 exige ritmo bem acima do praticado."),
    ("MARGEM_CONTRIB", "Unico KPI comercial acima da meta. RS abaixo por mix "
                       "concentrado em linha de entrada."),
    ("BASE_ATIVA", "A base cresce pouco em termos liquidos: metade do esforco "
                   "de captacao e consumido por inativacoes."),
    ("OTIF", "RS entrega a menor fatia do volume e responde pela maior parte "
             "dos pedidos com problema. Seu OTIF puxa o consolidado."),
    ("COBERTURA_ESTOQUE", "RS tem ao mesmo tempo a maior cobertura e estoque em "
                          "ruptura: excesso de SKU errado e falta do que gira."),
    ("INADIMPLENCIA", "Cai no mes, mas segue acima da meta. O ritmo de "
                      "recuperacao nao fecha o gap na semana 4."),
    ("CUSTO_POR_LEAD", "RS tem o pior custo por lead qualificado porque "
                       "qualifica pouco do que recebe."),
]


def _d(v) -> Decimal:
    return Decimal(str(v))


def main() -> int:
    settings = get_settings()
    if settings.is_production:
        print("ABORTADO: seed de dados ficticios nao roda em producao.")
        return 1

    senha = settings.SEED_SENHA_PADRAO
    if not senha:
        print("ABORTADO: defina SEED_SENHA_PADRAO em backend/.env.")
        return 1

    db = SessionLocal()
    criados = {k: 0 for k in (
        "usuarios", "regionais", "indicadores", "metas", "medicoes",
        "detalhamentos", "clientes", "ocorrencias", "titulos",
        "compromissos", "notas", "fontes",
    )}

    try:
        # --- acesso ---------------------------------------------------
        senha_hash = hash_senha(senha)
        for nome, email, perfil in USUARIOS:
            if db.scalar(select(Usuario).where(Usuario.email == email)):
                continue
            db.add(Usuario(nome=nome, email=email,
                           senha_hash=senha_hash, perfil=perfil))
            criados["usuarios"] += 1

        # --- fonte de dados -------------------------------------------
        fonte = db.scalar(select(FonteDados).where(FonteDados.codigo == "MANUAL_COMITE"))
        if fonte is None:
            fonte = FonteDados(
                codigo="MANUAL_COMITE",
                nome="Lancamento manual no proprio sistema",
                tipo=TipoFonte.MANUAL,
                config={"observacao": "Base de trabalho enquanto o Supabase "
                                      "e as APIs de ERP/CRM nao estao ligados"},
            )
            db.add(fonte)
            criados["fontes"] += 1

        # --- regionais ------------------------------------------------
        regionais: dict[str, Regional] = {}
        for codigo, nome, ordem in REGIONAIS:
            r = db.scalar(select(Regional).where(Regional.codigo == codigo))
            if r is None:
                r = Regional(codigo=codigo, nome=nome, ordem=ordem)
                db.add(r)
                criados["regionais"] += 1
            regionais[codigo] = r
        db.flush()

        # --- ciclo ----------------------------------------------------
        ciclo = db.scalar(select(Ciclo).where(Ciclo.ano == 2026, Ciclo.mes == 8))
        if ciclo is None:
            ciclo = Ciclo(
                ano=2026, mes=8, semanas_total=SEMANAS,
                semana_corrente=SEMANA_CORRENTE,
                data_fechamento=date(2026, 8, 31),
            )
            db.add(ciclo)
        db.flush()

        # --- indicadores ----------------------------------------------
        indicadores: dict[str, Indicador] = {}
        for (codigo, nome, area, unidade, tipo, direcao,
             rot_num, rot_den, ordem) in INDICADORES:
            ind = db.scalar(select(Indicador).where(Indicador.codigo == codigo))
            if ind is None:
                ind = Indicador(
                    codigo=codigo, nome=nome, area=area, unidade=unidade,
                    tipo_acumulacao=tipo, melhor_direcao=direcao,
                    rotulo_numerador=rot_num, rotulo_denominador=rot_den,
                    ordem=ordem,
                )
                db.add(ind)
                criados["indicadores"] += 1
            indicadores[codigo] = ind
        db.flush()

        # --- metas consolidadas ---------------------------------------
        for codigo, valor in METAS.items():
            ind = indicadores[codigo]
            existe = db.scalar(select(Meta).where(
                Meta.indicador_id == ind.id, Meta.ciclo_id == ciclo.id,
                Meta.regional_id.is_(None),
            ))
            if existe is None:
                db.add(Meta(indicador_id=ind.id, ciclo_id=ciclo.id,
                            regional_id=None, valor=_d(valor)))
                criados["metas"] += 1

        # --- metas por regional ---------------------------------------
        for codigo, por_regional in METAS_REGIONAIS.items():
            ind = indicadores[codigo]
            for reg_codigo, valor in por_regional.items():
                reg = regionais[reg_codigo]
                existe = db.scalar(select(Meta).where(
                    Meta.indicador_id == ind.id, Meta.ciclo_id == ciclo.id,
                    Meta.regional_id == reg.id,
                ))
                if existe is None:
                    db.add(Meta(indicador_id=ind.id, ciclo_id=ciclo.id,
                                regional_id=reg.id, valor=_d(valor)))
                    criados["metas"] += 1

        # --- medicoes: os fatos-base ----------------------------------
        def lancar(codigo, semana, reg_codigo, num, den=None):
            ind = indicadores[codigo]
            reg = regionais[reg_codigo]
            existe = db.scalar(select(Medicao).where(
                Medicao.indicador_id == ind.id, Medicao.ciclo_id == ciclo.id,
                Medicao.semana == semana, Medicao.regional_id == reg.id,
            ))
            if existe is not None:
                return
            db.add(Medicao(
                indicador_id=ind.id, ciclo_id=ciclo.id, semana=semana,
                regional_id=reg.id, valor_numerador=_d(num),
                valor_denominador=_d(den) if den is not None else None,
                fonte_id=fonte.id,
            ))
            criados["medicoes"] += 1

        for codigo, por_regional in FATOS_ACUMULA.items():
            for reg_codigo, semanas in por_regional.items():
                for i, valor in enumerate(semanas, start=1):
                    lancar(codigo, i, reg_codigo, valor)

        for codigo, por_regional in FATOS_TAXA.items():
            for reg_codigo, semanas in por_regional.items():
                for i, (num, den) in enumerate(semanas, start=1):
                    lancar(codigo, i, reg_codigo, num, den)

        db.flush()

        # --- detalhamentos --------------------------------------------
        def detalhar(codigo, dimensao, categoria, valor, reg=None, ordem=0):
            ind = indicadores[codigo]
            existe = db.scalar(select(Detalhamento).where(
                Detalhamento.indicador_id == ind.id,
                Detalhamento.ciclo_id == ciclo.id,
                Detalhamento.dimensao == dimensao,
                Detalhamento.categoria == categoria,
                Detalhamento.regional_id == (reg.id if reg else None),
            ))
            if existe is not None:
                return
            db.add(Detalhamento(
                indicador_id=ind.id, ciclo_id=ciclo.id, semana=None,
                regional_id=reg.id if reg else None, dimensao=dimensao,
                categoria=categoria, valor=_d(valor), ordem=ordem,
            ))
            criados["detalhamentos"] += 1

        for i, (motivo, qtd) in enumerate(MOTIVOS_PERDA):
            detalhar("CONVERSAO_LEADS", "MOTIVO_PERDA", motivo, qtd, ordem=i)

        for reg_codigo, faixas in FAIXAS_COBERTURA.items():
            for i, (faixa, pct) in enumerate(faixas):
                detalhar("COBERTURA_ESTOQUE", "FAIXA_COBERTURA", faixa, pct,
                         reg=regionais[reg_codigo], ordem=i)

        # --- clientes -------------------------------------------------
        clientes: dict[str, Cliente] = {}
        for nome, reg_codigo, consultor in CLIENTES:
            c = db.scalar(select(Cliente).where(Cliente.nome == nome))
            if c is None:
                c = Cliente(nome=nome, regional_id=regionais[reg_codigo].id,
                            consultor=consultor)
                db.add(c)
                criados["clientes"] += 1
            clientes[nome] = c
        db.flush()

        # --- ocorrencias de entrega -----------------------------------
        for (nome, reg_codigo, causa, motivo, pedidos,
             plano, responsavel) in OCORRENCIAS:
            existe = db.scalar(select(OcorrenciaEntrega).where(
                OcorrenciaEntrega.ciclo_id == ciclo.id,
                OcorrenciaEntrega.semana == SEMANA_CORRENTE,
                OcorrenciaEntrega.cliente_rotulo == nome,
            ))
            if existe is not None:
                continue
            db.add(OcorrenciaEntrega(
                ciclo_id=ciclo.id, semana=SEMANA_CORRENTE,
                cliente_id=clientes[nome].id if nome in clientes else None,
                cliente_rotulo=nome,
                regional_id=regionais[reg_codigo].id if reg_codigo else None,
                causa=causa, motivo=motivo, pedidos_afetados=pedidos,
                plano_acao=plano, responsavel=responsavel,
            ))
            criados["ocorrencias"] += 1

        # --- titulos inadimplentes ------------------------------------
        for nome, valor, dias, negociando in TITULOS:
            existe = db.scalar(select(TituloInadimplente).where(
                TituloInadimplente.ciclo_id == ciclo.id,
                TituloInadimplente.semana == SEMANA_CORRENTE,
                TituloInadimplente.cliente_rotulo == nome,
            ))
            if existe is not None:
                continue
            c = clientes[nome]
            db.add(TituloInadimplente(
                ciclo_id=ciclo.id, semana=SEMANA_CORRENTE, cliente_id=c.id,
                cliente_rotulo=nome, regional_id=c.regional_id,
                consultor=c.consultor, valor_aberto=_d(valor),
                dias_atraso=dias, em_negociacao=negociando,
            ))
            criados["titulos"] += 1

        # --- compromissos ---------------------------------------------
        for frente, acao, responsavel, prazo, cod_ind, reg_codigo in COMPROMISSOS:
            existe = db.scalar(select(Compromisso).where(
                Compromisso.ciclo_id == ciclo.id, Compromisso.acao == acao,
            ))
            if existe is not None:
                continue
            db.add(Compromisso(
                ciclo_id=ciclo.id, semana_origem=SEMANA_CORRENTE,
                frente=frente, acao=acao, responsavel=responsavel, prazo=prazo,
                indicador_id=indicadores[cod_ind].id if cod_ind else None,
                regional_id=regionais[reg_codigo].id if reg_codigo else None,
            ))
            criados["compromissos"] += 1

        # --- notas ----------------------------------------------------
        for cod_ind, texto in NOTAS:
            ind_id = indicadores[cod_ind].id if cod_ind else None
            existe = db.scalar(select(NotaAnalitica).where(
                NotaAnalitica.ciclo_id == ciclo.id,
                NotaAnalitica.semana == SEMANA_CORRENTE,
                NotaAnalitica.indicador_id == ind_id,
            ))
            if existe is not None:
                continue
            db.add(NotaAnalitica(
                ciclo_id=ciclo.id, semana=SEMANA_CORRENTE,
                indicador_id=ind_id, texto=texto,
            ))
            criados["notas"] += 1

        db.commit()
    finally:
        db.close()

    total = sum(criados.values())
    if total == 0:
        print("Nada a criar — o ciclo ja estava carregado.")
    else:
        print("Seed do comite carregado:")
        for k, v in criados.items():
            if v:
                print(f"  {v:>4} {k}")
    print(f"\nCiclo 08/2026, semana {SEMANA_CORRENTE} de {SEMANAS}.")
    if criados["usuarios"]:
        print(f"Senha dos usuarios de teste: {senha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
