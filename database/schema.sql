-- =====================================================================
-- dir-dashboard — Relatorio gerencial do comite executivo
-- MySQL 8.0 / utf8mb4
--
-- Uso:  make db-schema
--
-- Desenho em quatro camadas:
--   0. Acesso      — usuarios, auditoria
--   1. Cadastro    — regionais, indicadores, ciclos, fontes de dados
--   2. Fatos       — metas, medicoes, detalhamentos
--   3. Nominal     — clientes, ocorrencias, titulos, compromissos, notas
--
-- Decisao central: indicadores de taxa guardam NUMERADOR e DENOMINADOR,
-- nunca o percentual pronto. O consolidado de uma taxa e
-- soma(numeradores)/soma(denominadores), nao a media das regionais.
-- Com OTIF: ponderado = 92,3% (correto), media simples = 89,5% (errado).
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '-03:00';

-- =====================================================================
-- 0. ACESSO
-- =====================================================================

-- ---------------------------------------------------------------------
-- usuarios
-- Perfis: ADMIN (tudo), USER (le e lanca dados), READ_ONLY (so le)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nome            VARCHAR(120)    NOT NULL,
    email           VARCHAR(180)    NOT NULL,
    senha_hash      VARCHAR(255)    NOT NULL,
    perfil          ENUM('ADMIN', 'USER', 'READ_ONLY') NOT NULL DEFAULT 'USER',
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    ultimo_acesso   DATETIME        NULL,
    criado_em       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_email (email),
    KEY idx_usuarios_perfil_ativo (perfil, ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- log_auditoria — rastro de acoes sensiveis
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS log_auditoria (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id      BIGINT UNSIGNED NULL,
    acao            VARCHAR(80)     NOT NULL COMMENT 'LOGIN, CRIAR, EDITAR, EXCLUIR',
    entidade        VARCHAR(60)     NULL,
    entidade_id     BIGINT UNSIGNED NULL,
    detalhe         JSON            NULL,
    ip              VARCHAR(45)     NULL,
    criado_em       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_log_usuario_data (usuario_id, criado_em),
    KEY idx_log_acao (acao),
    CONSTRAINT fk_log_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 1. CADASTRO
-- =====================================================================

-- ---------------------------------------------------------------------
-- regionais — a dimensao de quebra. "A acao e definida sobre a regional
-- fora do ritmo, nunca sobre a media da empresa."
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regionais (
    id          SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo      VARCHAR(10)  NOT NULL COMMENT 'SP, RJ, RS',
    nome        VARCHAR(80)  NOT NULL,
    ordem       SMALLINT     NOT NULL DEFAULT 0,
    ativo       TINYINT(1)   NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_regionais_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- indicadores — catalogo dos KPIs acompanhados no comite.
--
-- tipo_acumulacao define o atingimento ESPERADO na semana, que e a base
-- do semaforo:
--   ACUMULA — soma ao longo do mes (faturamento, leads, recuperacao).
--             Esperado na semana N de T = N/T. Na semana 3 de 4: 75%.
--   TAXA    — razao valida a qualquer momento (margem %, OTIF,
--             inadimplencia, tempo medio, cobertura). Esperado = 100%
--             em qualquer semana.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indicadores (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo          VARCHAR(60)  NOT NULL COMMENT 'Chave estavel, ex: FATURAMENTO',
    nome            VARCHAR(160) NOT NULL,
    descricao       TEXT         NULL,
    area            ENUM('COMERCIAL', 'OPERACOES', 'ESTOQUE',
                         'FINANCEIRO', 'MARKETING') NOT NULL,
    unidade         ENUM('BRL', 'BRL_MIL', 'BRL_MI', 'PCT', 'NUM',
                         'DIAS', 'CLIENTES', 'PEDIDOS', 'LEADS')
                    NOT NULL DEFAULT 'NUM',
    tipo_acumulacao ENUM('ACUMULA', 'TAXA') NOT NULL,
    melhor_direcao  ENUM('MAIOR', 'MENOR') NOT NULL DEFAULT 'MAIOR',

    -- Rotulos do numerador e do denominador, para a interface explicar a
    -- taxa ao leitor: "99 com problema sobre 1.284 pedidos".
    rotulo_numerador    VARCHAR(80) NULL,
    rotulo_denominador  VARCHAR(80) NULL,

    -- Indicador de apoio: aparece no detalhe do KPI pai, nao no painel
    -- geral. Ex: entradas e saidas dentro de "base ativa".
    indicador_pai_id    BIGINT UNSIGNED NULL,

    exibe_no_painel  TINYINT(1)  NOT NULL DEFAULT 1,
    ordem            SMALLINT    NOT NULL DEFAULT 0,
    ativo            TINYINT(1)  NOT NULL DEFAULT 1,
    criado_em        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_indicadores_codigo (codigo),
    KEY idx_indicadores_area (area, ordem),
    KEY idx_indicadores_painel (exibe_no_painel, ativo),
    CONSTRAINT fk_indicadores_pai
        FOREIGN KEY (indicador_pai_id) REFERENCES indicadores (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- ciclos — o mes de apuracao, dividido em semanas. "Semana 3 de 4,
-- fechamento em 31/08/2026."
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ciclos (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ano             SMALLINT UNSIGNED NOT NULL,
    mes             TINYINT  UNSIGNED NOT NULL,
    semanas_total   TINYINT  UNSIGNED NOT NULL DEFAULT 4,
    semana_corrente TINYINT  UNSIGNED NOT NULL DEFAULT 1
                    COMMENT 'Semana que o comite esta revisando',
    data_fechamento DATE     NOT NULL,
    status          ENUM('ABERTO', 'FECHADO') NOT NULL DEFAULT 'ABERTO',
    criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ciclos_ano_mes (ano, mes),
    KEY idx_ciclos_status (status),
    CONSTRAINT ck_ciclos_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_ciclos_semanas CHECK (semanas_total BETWEEN 1 AND 6),
    CONSTRAINT ck_ciclos_corrente CHECK (semana_corrente <= semanas_total)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- fontes_dados — de onde vem cada indicador. Hoje tudo e MANUAL no
-- MySQL; a coluna existe para plugar Supabase, ERP, CRM e planilhas sem
-- mexer na camada de KPI.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fontes_dados (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo          VARCHAR(60) NOT NULL COMMENT 'Ex: SUPABASE_VENDAS, ERP_TITULOS',
    nome            VARCHAR(160) NOT NULL,
    tipo            ENUM('MANUAL', 'SUPABASE', 'API_REST',
                         'PLANILHA', 'BANCO_EXTERNO') NOT NULL,
    -- Parametros de conexao NAO ficam aqui: segredo vive no ambiente.
    -- Este campo guarda apenas o que e seguro versionar (endpoint,
    -- nome de tabela, intervalo de sincronizacao).
    config          JSON        NULL,
    ativo           TINYINT(1)  NOT NULL DEFAULT 1,
    ultima_sincronia DATETIME   NULL,
    criado_em       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_fontes_codigo (codigo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 2. FATOS
-- =====================================================================

-- ---------------------------------------------------------------------
-- metas — o alvo do mes. regional_id NULL = meta consolidada da empresa.
-- Uma meta por regional e opcional: quando ausente, o painel compara a
-- regional contra a fatia proporcional da meta consolidada.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS metas (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    indicador_id  BIGINT UNSIGNED NOT NULL,
    ciclo_id      BIGINT UNSIGNED NOT NULL,
    regional_id   SMALLINT UNSIGNED NULL COMMENT 'NULL = consolidado',
    valor         DECIMAL(18, 4) NOT NULL,
    observacao    VARCHAR(300)   NULL,
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    -- regional_id NULL nao participa de UNIQUE no MySQL, entao a coluna
    -- gerada normaliza NULL para 0 e garante uma meta por combinacao.
    -- VIRTUAL e nao STORED: o InnoDB recusa ON DELETE CASCADE numa
    -- coluna-base de generated column STORED. VIRTUAL aceita indice
    -- secundario e nao ocupa espaco.
    regional_key  SMALLINT UNSIGNED AS (COALESCE(regional_id, 0)) VIRTUAL,
    UNIQUE KEY uq_metas (indicador_id, ciclo_id, regional_key),
    KEY idx_metas_ciclo (ciclo_id),
    CONSTRAINT fk_metas_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_metas_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_metas_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- medicoes — o realizado, por indicador, ciclo, semana e regional.
--
-- Sempre por regional: o consolidado e derivado, nunca digitado, para
-- nao existirem duas versoes da verdade.
--
-- valor_numerador   — o valor em si (ACUMULA) ou o numerador (TAXA)
-- valor_denominador — apenas para TAXA. Permite consolidar corretamente:
--                     soma(num)/soma(den), e nao a media das regionais.
--
-- ACUMULA guarda o valor da SEMANA, nao o acumulado. O acumulado do mes
-- e a soma das semanas — assim uma correcao em S2 nao exige recalcular
-- S3 e S4 a mao.
-- TAXA guarda a posicao DAQUELA semana (e um retrato, nao um fluxo).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicoes (
    id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    indicador_id      BIGINT UNSIGNED NOT NULL,
    ciclo_id          BIGINT UNSIGNED NOT NULL,
    semana            TINYINT UNSIGNED NOT NULL,
    regional_id       SMALLINT UNSIGNED NOT NULL,
    valor_numerador   DECIMAL(18, 4) NOT NULL,
    valor_denominador DECIMAL(18, 4) NULL,
    observacao        VARCHAR(300)   NULL,
    fonte_id          BIGINT UNSIGNED NULL,
    registrado_por    BIGINT UNSIGNED NULL,
    criado_em         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_medicoes (indicador_id, ciclo_id, semana, regional_id),
    KEY idx_medicoes_ciclo_semana (ciclo_id, semana),
    KEY idx_medicoes_indicador (indicador_id, ciclo_id),
    CONSTRAINT ck_medicoes_semana CHECK (semana BETWEEN 1 AND 6),
    -- Denominador zero produziria divisao por zero na taxa.
    CONSTRAINT ck_medicoes_denominador
        CHECK (valor_denominador IS NULL OR valor_denominador <> 0),
    CONSTRAINT fk_medicoes_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_medicoes_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_medicoes_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_medicoes_fonte
        FOREIGN KEY (fonte_id) REFERENCES fontes_dados (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_medicoes_usuario
        FOREIGN KEY (registrado_por) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- detalhamentos — quebra de um indicador por categoria, para as visoes
-- que o comite abre no detalhe: motivos de perda de lead, faixas de
-- cobertura de estoque, composicao de entradas e saidas.
--
-- Generico de proposito: uma pergunta nova no comite ("abra as perdas
-- por faixa de desconto") entra como categoria, sem alterar o schema.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detalhamentos (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    indicador_id  BIGINT UNSIGNED NOT NULL,
    ciclo_id      BIGINT UNSIGNED NOT NULL,
    semana        TINYINT UNSIGNED NULL COMMENT 'NULL = acumulado do mes',
    regional_id   SMALLINT UNSIGNED NULL COMMENT 'NULL = consolidado',
    dimensao      VARCHAR(60)  NOT NULL COMMENT 'Ex: MOTIVO_PERDA, FAIXA_COBERTURA',
    categoria     VARCHAR(160) NOT NULL COMMENT 'Ex: Preco acima do concorrente',
    valor         DECIMAL(18, 4) NOT NULL,
    ordem         SMALLINT     NOT NULL DEFAULT 0,
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_detalhamentos_busca (indicador_id, ciclo_id, dimensao),
    CONSTRAINT fk_detalhamentos_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_detalhamentos_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_detalhamentos_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================================
-- 3. NOMINAL — o detalhe que transforma diagnostico em acao.
--    Cliente, causa, responsavel, prazo.
-- =====================================================================

-- ---------------------------------------------------------------------
-- clientes — cadastro minimo, o suficiente para nomear a quebra.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo_externo VARCHAR(60)  NULL COMMENT 'Chave no ERP, para reconciliar',
    nome         VARCHAR(180)   NOT NULL,
    regional_id  SMALLINT UNSIGNED NULL,
    consultor    VARCHAR(120)   NULL,
    ativo        TINYINT(1)     NOT NULL DEFAULT 1,
    criado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_clientes_codigo_externo (codigo_externo),
    KEY idx_clientes_regional (regional_id),
    KEY idx_clientes_nome (nome),
    CONSTRAINT fk_clientes_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- ocorrencias_entrega — os pedidos com problema da semana, por cliente,
-- causa e plano de acao.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocorrencias_entrega (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ciclo_id       BIGINT UNSIGNED NOT NULL,
    semana         TINYINT UNSIGNED NOT NULL,
    cliente_id     BIGINT UNSIGNED NULL COMMENT 'NULL para linhas agregadas',
    cliente_rotulo VARCHAR(180) NOT NULL COMMENT 'Ex: "Outros 11 clientes"',
    regional_id    SMALLINT UNSIGNED NULL,
    causa          VARCHAR(60)  NOT NULL COMMENT 'RUPTURA_ESTOQUE, ATRASO_TRANSPORTE...',
    motivo         VARCHAR(300) NOT NULL,
    pedidos_afetados SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    plano_acao     VARCHAR(300) NULL,
    responsavel    VARCHAR(120) NULL,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_ocorrencias_ciclo (ciclo_id, semana),
    KEY idx_ocorrencias_causa (causa),
    CONSTRAINT fk_ocorrencias_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ocorrencias_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_ocorrencias_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- titulos_inadimplentes — a carteira em aberto, cliente a cliente.
-- Sustenta a leitura 80/20: 8 clientes com 77% do valor.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS titulos_inadimplentes (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ciclo_id       BIGINT UNSIGNED NOT NULL,
    semana         TINYINT UNSIGNED NOT NULL,
    cliente_id     BIGINT UNSIGNED NULL,
    cliente_rotulo VARCHAR(180) NOT NULL,
    regional_id    SMALLINT UNSIGNED NULL,
    consultor      VARCHAR(120)   NULL,
    valor_aberto   DECIMAL(18, 2) NOT NULL,
    dias_atraso    SMALLINT UNSIGNED NULL,
    em_negociacao  TINYINT(1)     NOT NULL DEFAULT 0,
    observacao     VARCHAR(300)   NULL,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_titulos_ciclo (ciclo_id, semana),
    KEY idx_titulos_valor (ciclo_id, valor_aberto DESC),
    CONSTRAINT fk_titulos_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_titulos_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_titulos_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- compromissos — o que o comite decidiu, com responsavel e prazo.
--
-- indicador_id liga a acao ao KPI que ela deve mover, para a proxima
-- reuniao cobrar o resultado: "cada compromisso volta ao painel como
-- movimento esperado no KPI correspondente."
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compromissos (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ciclo_id       BIGINT UNSIGNED NOT NULL COMMENT 'Ciclo em que foi assumido',
    semana_origem  TINYINT UNSIGNED NOT NULL,
    frente         VARCHAR(120) NOT NULL COMMENT 'Ex: "RS · Faturamento"',
    acao           VARCHAR(400) NOT NULL,
    responsavel    VARCHAR(120) NOT NULL,
    prazo          DATE         NOT NULL,
    indicador_id   BIGINT UNSIGNED NULL COMMENT 'KPI que deve se mover',
    regional_id    SMALLINT UNSIGNED NULL,
    status         ENUM('ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO',
                        'CANCELADO', 'ATRASADO') NOT NULL DEFAULT 'ABERTO',
    resultado      VARCHAR(400) NULL COMMENT 'Preenchido na revisao seguinte',
    criado_por     BIGINT UNSIGNED NULL,
    criado_em      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_compromissos_ciclo (ciclo_id, semana_origem),
    KEY idx_compromissos_status (status, prazo),
    KEY idx_compromissos_indicador (indicador_id),
    CONSTRAINT fk_compromissos_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_compromissos_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_compromissos_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_compromissos_usuario
        FOREIGN KEY (criado_por) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- notas_analiticas — a leitura que o comite registra sobre um KPI numa
-- semana. E o texto de rodape de cada slide ("RS e a quebra principal"),
-- que hoje se perde entre reunioes.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notas_analiticas (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ciclo_id      BIGINT UNSIGNED NOT NULL,
    semana        TINYINT UNSIGNED NOT NULL,
    indicador_id  BIGINT UNSIGNED NULL COMMENT 'NULL = nota do painel geral',
    regional_id   SMALLINT UNSIGNED NULL,
    texto         TEXT     NOT NULL,
    autor_id      BIGINT UNSIGNED NULL,
    criado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_notas_busca (ciclo_id, semana, indicador_id),
    CONSTRAINT fk_notas_ciclo
        FOREIGN KEY (ciclo_id) REFERENCES ciclos (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notas_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notas_regional
        FOREIGN KEY (regional_id) REFERENCES regionais (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_notas_autor
        FOREIGN KEY (autor_id) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
