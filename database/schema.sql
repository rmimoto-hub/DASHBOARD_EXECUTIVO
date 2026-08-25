-- =====================================================================
-- dir-dashboard — Schema do banco de dados
-- MySQL 8.0 / utf8mb4
--
-- Uso:
--   mysql -u root dir_dashboard < database/schema.sql
-- ou, no MySQL Workbench:
--   source database/schema.sql
-- =====================================================================

SET NAMES utf8mb4;
SET time_zone = '-03:00';

-- ---------------------------------------------------------------------
-- usuarios
-- Perfis: ADMIN (tudo), USER (leitura + escrita), READ_ONLY (leitura)
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
-- indicadores — catálogo de KPIs do painel executivo
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indicadores (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo          VARCHAR(60)     NOT NULL COMMENT 'Chave estavel, ex: FAT_MENSAL',
    nome            VARCHAR(160)    NOT NULL,
    descricao       TEXT            NULL,
    unidade         VARCHAR(20)     NOT NULL DEFAULT 'NUM'
                                    COMMENT 'BRL, PCT, NUM, DIAS',
    area            VARCHAR(60)     NOT NULL DEFAULT 'GERAL'
                                    COMMENT 'COMERCIAL, FINANCEIRO, OPERACOES...',
    melhor_direcao  ENUM('MAIOR', 'MENOR') NOT NULL DEFAULT 'MAIOR'
                                    COMMENT 'Se subir e bom ou ruim',
    ativo           TINYINT(1)      NOT NULL DEFAULT 1,
    criado_em       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_indicadores_codigo (codigo),
    KEY idx_indicadores_area_ativo (area, ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- medicoes — valor de um indicador em uma competência (mês)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicoes (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    indicador_id    BIGINT UNSIGNED NOT NULL,
    competencia     DATE            NOT NULL COMMENT 'Sempre dia 01 do mes',
    valor           DECIMAL(18, 4)  NOT NULL,
    meta            DECIMAL(18, 4)  NULL,
    observacao      VARCHAR(500)    NULL,
    registrado_por  BIGINT UNSIGNED NULL,
    criado_em       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_medicoes_indicador_competencia (indicador_id, competencia),
    KEY idx_medicoes_competencia (competencia),
    CONSTRAINT fk_medicoes_indicador
        FOREIGN KEY (indicador_id) REFERENCES indicadores (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_medicoes_usuario
        FOREIGN KEY (registrado_por) REFERENCES usuarios (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- log_auditoria — rastro de ações sensíveis
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
