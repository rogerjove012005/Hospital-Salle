# ADR 001 — Almacenamiento dual PostgreSQL + MinIO

**Estado:** Aceptado  
**Fecha:** 2026-05

## Contexto

El enunciado exige al menos dos tipos de almacenamiento (estructurado + no estructurado). Se evaluó MongoDB para documentos e imágenes.

## Decisión

- **PostgreSQL 16** para datos relacionales: usuarios, pacientes, estudios, lotes CSV, agregados, eventos, calidad.
- **MinIO** (API S3) para objetos: radiografías y ficheros binarios.

## Consecuencias

**Ventajas:** SQL auditable, joins con dominio clínico, MinIO ligero en Docker, SDK estándar S3.

**Inconvenientes:** No hay esquema flexible tipo documento para CSV crudo; las filas se normalizan en tablas.

## Alternativas descartadas

| Alternativa | Motivo de descarte |
|-------------|-------------------|
| MongoDB único | Menos natural para RBAC y agregados Spark vía JDBC |
| Solo filesystem | No cumple patrón Big Data ni escalado objeto |
| PostgreSQL BYTEA para imágenes | Aumenta tamaño de backups y complejidad |
