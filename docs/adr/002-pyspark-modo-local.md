# ADR 002 — PySpark en modo `local[*]`

**Estado:** Aceptado  
**Fecha:** 2026-05

## Contexto

Requisito: framework de procesamiento distribuido o escalable (Spark, Dask, Beam). El equipo no dispone de cluster YARN/Kubernetes en el entorno docente.

## Decisión

Usar **Apache Spark / PySpark** con master `local[*]` en contenedor dedicado, leyendo y escribiendo vía **JDBC** a PostgreSQL y exportando **Parquet** a volumen Docker.

## Consecuencias

**Ventajas:** Cumple literal del enunciado; mismo código migrable a cluster; API DataFrame familiar.

**Inconvenientes:** No demuestra paralelismo real multi-nodo; consumo RAM del driver en máquinas lentas.

## Alternativas consideradas

| Framework | Motivo |
|-----------|--------|
| Dask | Menor alineación con currículo «Sistemas Big Data» del máster |
| Pandas | No escalable por diseño |
| Beam | Mayor curva para job batch simple |

## Evolución

En producción: `spark.master` → `k8s://...` o `yarn`, particionar lectura JDBC por `batch_id`.
