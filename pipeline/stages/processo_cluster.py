
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from ..core._stage_base import RunContext, StageMeta
from ..evidence.artifact import write_artifact
from ..model.cluster_metrics import assign_noise_to_nearest, evaluate_clustering
from ..model.clustering import NOISE_LABEL, build_catalog, category_id, cluster_macro, cluster_micro_within, dedupe_macro_labels, name_all_clusters
from ..core.cypher import CLEAR_CATEGORIA_PROCESSO_CYPHER, LOAD_CATEGORIA_PROCESSO_CYPHER, LOAD_CATEGORIZADO_COMO_CYPHER, LOAD_CLUSTERING_RUN_CYPHER, LOAD_SUBCATEGORIA_DE_CYPHER, READ_ALL_CLUSTER_FEATURES_CYPHER, READ_PROCESSO_TIPO_CYPHER, SAMPLE_PROCESSOS_FOR_NAMING_CYPHER
from ..model.ner_llm import NerLLM, config_from_settings
from ..core.registry import stage
from ..core.state import now_iso
from ..core.paths import ARTIFACTS

log = logging.getLogger(__name__)


def _build_llm_call(settings):
    cfg = config_from_settings(settings, model="Qwen/Qwen3.6-35B-A3B")
    llm = NerLLM(cfg)

    def _call(messages: list[dict[str, str]]) -> str:
        resp = llm._client.chat.completions.create(
            model=cfg.model,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    return _call


def _build_sample_loader(driver):
    def _load(protocolos: list[str]) -> list[dict[str, Any]]:
        if not protocolos:
            return []
        with driver.session() as session:
            result = session.run(SAMPLE_PROCESSOS_FOR_NAMING_CYPHER, protocolos=protocolos)
            return [dict(r) for r in result]

    return _load


_MICRO_PROFILE_CYPHER = """
UNWIND $protos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
OPTIONAL MATCH (p)-[:TEM_TIPO]->(t:TipoProcedimento)
OPTIONAL MATCH (p)<-[:DO_PROCESSO]-(a:Atividade)
RETURN pf AS pf, t.nome AS tipo, count(a) AS natv
"""


_EXPORT_ATTRS_CYPHER = """
UNWIND $protos AS pf
MATCH (p:Processo {protocolo_formatado: pf})
OPTIONAL MATCH (p)-[:TEM_TIPO]->(t:TipoProcedimento)
RETURN p.protocolo_formatado AS pf,
       coalesce(p.unidades_em_aberto_count, 0) AS open_units,
       t.nome AS tipo
"""

_EXPORT_CATS_CYPHER = """
MATCH (c:CategoriaProcesso {nivel:'macro'})
RETURN c.id AS id, c.nome AS nome, c.descricao AS descricao,
       c.marcadores AS marcadores, coalesce(c.n_processos, 0) AS n_members
"""


def _export_catalog_artifacts(driver, run_id: str, protocolos, macro_labels) -> list[str]:
    if not run_id or driver is None:
        return []
    from ..model.cluster_catalog import aggregate_catalog

    labels = {pf: int(m) for pf, m in zip(protocolos, macro_labels)}
    attrs: dict[str, dict] = {}
    with driver.session() as session:
        keys = list(labels)
        for i in range(0, len(keys), 5000):
            for r in session.run(_EXPORT_ATTRS_CYPHER, protos=keys[i:i + 5000]):
                attrs[r["pf"]] = {"open_units": r["open_units"], "tipo": r["tipo"]}
        cats = [dict(r) for r in session.run(_EXPORT_CATS_CYPHER)]

    out_dir = ARTIFACTS / "clustering" / run_id / "hdbscan"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    catalog = aggregate_catalog(labels, attrs)
    write_artifact({"meta": {"run": run_id, "algo": "hdbscan"}, "catalog": catalog},
                   out_dir / "cluster_catalog.json", force=True, stage="processo-cluster",
                   params={"run_id": run_id, "algo": "hdbscan"})
    written.append(str(out_dir / "cluster_catalog.json"))

    names = {}
    for c in cats:
        marc = c.get("marcadores") or []
        if isinstance(marc, str):
            marc = [marc]
        names[c["id"]] = {"nome": c.get("nome") or "", "descricao": c.get("descricao") or "",
                          "marcadores": marc[:8], "n_members": c["n_members"]}
    write_artifact({"meta": {"run": run_id, "algo": "hdbscan"}, "names": names},
                   out_dir / "names.json", force=True, stage="processo-cluster",
                   params={"run_id": run_id, "algo": "hdbscan"})
    written.append(str(out_dir / "names.json"))
    log.info("processo-cluster: exported %d clusters / %d names to %s",
             len(catalog), len(names), out_dir)
    return written


def _build_micro_profiles(driver, catalog, run_id: str) -> dict[str, str]:
    from collections import Counter, defaultdict
    proto_to_cid: dict[str, str] = {}
    for desc in catalog.micro_clusters:
        cid = category_id(run_id, desc.nivel, desc.micro_label, desc.macro_label)
        for pf in desc.member_protocolos:
            proto_to_cid[pf] = cid
    if not proto_to_cid:
        return {}

    agg: dict[str, dict] = defaultdict(lambda: {"tipos": Counter(), "natv": []})
    protos = list(proto_to_cid)
    with driver.session() as session:
        for i in range(0, len(protos), 2000):
            for r in session.run(_MICRO_PROFILE_CYPHER, protos=protos[i:i + 2000]):
                cid = proto_to_cid.get(r["pf"])
                if not cid:
                    continue
                if r["tipo"]:
                    agg[cid]["tipos"][r["tipo"]] += 1
                agg[cid]["natv"].append(r["natv"])

    profiles: dict[str, str] = {}
    for cid, a in agg.items():
        natv = a["natv"]
        n = len(natv)
        avg = sum(natv) / n if n else 0.0
        band = "curto" if avg < 50 else ("médio" if avg < 150 else "longo")
        tipo = a["tipos"].most_common(1)[0][0] if a["tipos"] else "?"
        profiles[cid] = f"{n} processos, porte {band} (~{avg:.0f} atividades), tipo predominante: {tipo[:45]}"
    return profiles


def cluster_top_keywords(member_protocolos, keywords_by_pf, *, limit: int = 12):
    from collections import Counter

    counts: Counter = Counter()
    for pf in member_protocolos:
        for kw in keywords_by_pf.get(pf) or []:
            counts[kw] += 1
    return counts.most_common(limit)


def _build_macro_profiles(driver, catalog, run_id: str, sample_size: int = 60) -> dict[str, str]:
    profiles: dict[str, str] = {}
    with driver.session() as session:
        for desc in catalog.macro_clusters:
            cid = category_id(run_id, "macro", desc.macro_label)
            protos = desc.member_protocolos[:sample_size]
            if not protos:
                continue
            tipo = session.run(
                "UNWIND $protos AS pf MATCH (p:Processo {protocolo_formatado:pf})-[:TEM_TIPO]->(t) "
                "RETURN t.nome AS n, count(*) AS c ORDER BY c DESC LIMIT 1", protos=protos).single()
            flow = session.run(
                "UNWIND $protos AS pf MATCH (p:Processo {protocolo_formatado:pf})<-[:DO_PROCESSO]-"
                "(a:Atividade)-[:SEGUIDA_POR]->(b:Atividade)-[:DO_PROCESSO]->(p) "
                "RETURN a.tipo_acao+' → '+b.tipo_acao AS t, count(*) AS c ORDER BY c DESC LIMIT 2",
                protos=protos).data()
            topics = session.run(
                "UNWIND $protos AS pf MATCH (p:Processo {protocolo_formatado:pf})<-[:DO_PROCESSO]-"
                "(:Atividade)-[:REFERENCIA_DOCUMENTO]->(dd:Documento) WHERE dd.topic IS NOT NULL "
                "RETURN DISTINCT dd.topic AS t LIMIT 4", protos=protos).data()
            parts = [f"{len(desc.member_protocolos)} processos"]
            if tipo and tipo["n"]:
                parts.append(f"tipo {tipo['n'][:40]}")
            if flow:
                parts.append("fluxo: " + " ; ".join(f["t"][:44] for f in flow))
            if topics:
                parts.append("temas: " + " ; ".join(t["t"][:36] for t in topics))
            profiles[cid] = "; ".join(parts)
    return profiles


@stage(StageMeta(
    name="processo-cluster",
    phase="clustering",
    question="Que familias de processo emergem, e como se chamam?",
    deterministic=False,
    nondeterminism="a nomeacao dos grupos e feita por LLM",
    description="Clustering hierárquico de processos (HDBSCAN macro+micro) + LLM naming + :CategoriaProcesso.",
    type="enrich",
    depends_on=("processo-embed",),
    modes=("neo4j",),
    estimated_duration="~5-15min HDBSCAN + 1-3min naming via Mandu",
))
def run(ctx: RunContext) -> None:
    driver = ctx.require_driver()
    writer = ctx.require_writer()

    algo_flag = ctx.flags.get("algo")
    if algo_flag and algo_flag != "hdbscan":
        raise ValueError(
            f"processo-cluster only writes :CategoriaProcesso from HDBSCAN; "
            f"for algo={algo_flag!r} use the 'cluster-eval' stage"
        )

    macro_min = int(ctx.flags.get("macro_min_cluster_size") or 20)
    micro_min = int(ctx.flags.get("micro_min_cluster_size") or 5)
    samples_per_cluster = int(ctx.flags.get("samples_per_cluster") or 5)
    naming_workers = max(1, int(ctx.flags.get("naming_workers") or ctx.flags.get("workers") or 8))
    skip_naming = bool(ctx.flags.get("skip_naming", False))
    run_id = ctx.flags.get("run_id") or uuid.uuid4().hex[:12]
    macro_dedup_threshold = float(ctx.flags.get("macro_dedup_threshold") or 0.0)
    assign_noise = str(ctx.flags.get("assign_noise", "true")).strip().lower() \
        not in ("false", "0", "no")
    want_dbcv = str(ctx.flags.get("compute_dbcv", "true")).strip().lower() not in ("false", "0", "no")

    log.info(
        "processo-cluster: macro_min=%d, micro_min=%d, samples=%d, macro_dedup=%.2f, run_id=%s",
        macro_min, micro_min, samples_per_cluster, macro_dedup_threshold, run_id,
    )

    from .cluster_eval import _ARM_VARIANT, _arm_of, _load_features_from_npz

    features_file = ctx.flags.get("features_file")
    arm = _arm_of(run_id)
    if arm and not features_file:
        raise ValueError(
            f"run_id={run_id!r} names the {arm!r} arm, but no features_file was given. "
            f"Neo4j cluster_features hold whichever arm was embedded last. "
            f"Pass --flag features_file=artifacts/features/{arm}.npz"
        )

    protocolos: list[str] = []
    feature_rows: list[list[float]] = []
    if features_file:
        protocolos, feats, stamp = _load_features_from_npz(features_file)
        feature_rows = feats.tolist()
        want, got = _ARM_VARIANT.get(arm or ""), stamp.get("text_variant")
        if want and got and got not in ("unknown", want):
            raise ValueError(
                f"run_id={run_id!r} is the {want!r} arm but {features_file} was built from "
                f"text_variant={got!r}. Refusing to produce a mislabelled catalog."
            )
        log.info("processo-cluster: loaded %d features from %s (digest=%s variant=%s)",
                 len(protocolos), features_file, stamp.get("digest", "-"), got or "-")
    else:
        with driver.session() as session:
            for r in session.run(READ_ALL_CLUSTER_FEATURES_CYPHER):
                f = r.get("features")
                if not f:
                    continue
                protocolos.append(r["protocolo"])
                feature_rows.append(list(f))

    if not feature_rows:
        log.error("processo-cluster: no features available. Run processo-embed first.")
        ctx.cache["processo_cluster_summary"] = {"error": "no_features", "total": 0}
        return

    features = np.asarray(feature_rows, dtype=np.float64)
    log.info("processo-cluster: %d processos × %d dims loaded", *features.shape)

    log.info("processo-cluster: running HDBSCAN macro (min=%d)...", macro_min)
    macro_labels, macro_str = cluster_macro(features, min_cluster_size=macro_min)
    n_macro_raw = len(set(int(x) for x in macro_labels) - {NOISE_LABEL})
    if macro_dedup_threshold > 0:
        macro_labels = dedupe_macro_labels(features, macro_labels, threshold=macro_dedup_threshold)
        n_macro = len(set(int(x) for x in macro_labels) - {NOISE_LABEL})
        log.info(
            "processo-cluster: macro de-dup (sep_ratio<=%.2f) merged %d → %d clusters",
            macro_dedup_threshold, n_macro_raw, n_macro,
        )
    n_noise_before = int((macro_labels == NOISE_LABEL).sum())
    assign_params: dict = {}
    if n_noise_before and assign_noise:
        macro_labels = assign_noise_to_nearest(features, macro_labels)
        assign_params = {
            "assign_noise": True,
            "noise_ratio_before_assignment": round(n_noise_before / len(macro_labels), 4),
            "n_reassigned": n_noise_before,
        }
        log.info("processo-cluster: assigned %d macro outliers to their nearest cluster so the "
                 "published partition covers the same population as every other algorithm",
                 n_noise_before)
    elif n_noise_before:
        assign_params = {
            "assign_noise": False,
            "noise_ratio_before_assignment": round(n_noise_before / len(macro_labels), 4),
        }

    n_macro = len(set(int(x) for x in macro_labels) - {NOISE_LABEL})
    n_macro_outliers = int((macro_labels == NOISE_LABEL).sum())
    log.info("processo-cluster: macro found %d clusters + %d outliers", n_macro, n_macro_outliers)

    ref_map: dict[str, Any] = {}
    with driver.session() as session:
        for r in session.run(READ_PROCESSO_TIPO_CYPHER):
            ref_map[r["protocolo"]] = r.get("tipo_procedimento")
    reference = [ref_map.get(pf) for pf in protocolos]
    macro_metrics = evaluate_clustering(
        features, macro_labels, algo="hdbscan",
        params={"min_cluster_size": macro_min, "macro_dedup_threshold": macro_dedup_threshold,
                **assign_params},
        reference=reference,
    )
    dbcv_macro = macro_metrics["dbcv"]
    macro_silhouette = macro_metrics["silhouette"]
    macro_noise_ratio = macro_metrics["noise_ratio"]
    if want_dbcv:
        if dbcv_macro is not None:
            log.info("processo-cluster: DBCV (macro) = %.4f  (higher is better, max 1.0)", dbcv_macro)
        else:
            log.info("processo-cluster: DBCV (macro) = n/a (undefined or uncomputable)")

    log.info("processo-cluster: running HDBSCAN micro per macro group (min=%d)...", micro_min)
    micro_labels, micro_str, reclassificada = cluster_micro_within(
        features, macro_labels, min_cluster_size=micro_min,
    )
    n_micro = len(set((int(m), int(s)) for m, s in zip(macro_labels, micro_labels)
                       if int(s) != NOISE_LABEL))
    n_rescued = int(reclassificada.sum())
    log.info(
        "processo-cluster: micro found %d sub-clusters; %d processos rescued (reclassificada=true)",
        n_micro, n_rescued,
    )

    if ctx.flags.get("run_id"):
        art_dir = ARTIFACTS / "clustering" / run_id / "hdbscan"
        labels_payload = {
            "meta": {"run_id": run_id, "algo": "hdbscan", "generated_at": now_iso(), "n": len(protocolos)},
            "labels": {pf: int(m) for pf, m in zip(protocolos, macro_labels)},
        }
        for payload, fname in ((labels_payload, "labels.json"), (macro_metrics, "metrics.json")):
            try:
                write_artifact(payload, art_dir / fname, stage="processo-cluster",
                               params={"run_id": run_id, "algo": "hdbscan"})
                log.info("processo-cluster: wrote %s", art_dir / fname)
            except FileExistsError:
                log.warning("processo-cluster: %s exists — not overwriting (frozen artifact)", art_dir / fname)
    else:
        log.warning("processo-cluster: no run_id flag — skipping artifacts/clustering/<run_id> write")

    catalog = build_catalog(
        run_id=run_id,
        protocolos=protocolos, features=features,
        macro_labels=macro_labels, macro_strengths=macro_str,
        micro_labels=micro_labels, micro_strengths=micro_str,
        reclassificada=reclassificada,
    )

    cluster_names: dict[str, dict[str, Any]] = {}
    if skip_naming:
        log.info("processo-cluster: --flag skip_naming=true — using placeholder names")
        for desc in catalog.macro_clusters:
            cid = category_id(run_id, "macro", desc.macro_label)
            cluster_names[cid] = {
                "nome": f"Macro #{desc.macro_label}",
                "descricao": f"{len(desc.member_protocolos)} processos",
                "marcadores": [],
            }
        for desc in catalog.micro_clusters:
            cid = category_id(run_id, desc.nivel, desc.micro_label, desc.macro_label)
            cluster_names[cid] = {
                "nome": f"{desc.nivel} #{desc.macro_label}.{desc.micro_label}",
                "descricao": f"{len(desc.member_protocolos)} processos",
                "marcadores": [],
            }
    else:
        log.info(
            "processo-cluster: naming %d clusters via LLM (Qwen/Qwen3.6-35B-A3B), %d workers...",
            len(catalog.macro_clusters) + len(catalog.micro_clusters), naming_workers,
        )
        loader = _build_sample_loader(driver)
        llm_call = _build_llm_call(ctx.settings)
        profiles = _build_micro_profiles(driver, catalog, run_id)
        from .processo_embed import load_keywords_by_processo
        kw_by_pf = load_keywords_by_processo(ctx.flags.get("parsed_dir") or "./parsed_documents")
        log.info("processo-cluster: keywords available for %d processos (naming context)",
                 len(kw_by_pf))
        macro_profiles = _build_macro_profiles(driver, catalog, run_id)
        log.info("processo-cluster: built %d micro + %d macro profiles for contrastive naming",
                 len(profiles), len(macro_profiles))
        cluster_names = name_all_clusters(
            catalog, loader, llm_call,
            samples_per_cluster=samples_per_cluster,
            workers=naming_workers,
            profiles=profiles,
            macro_profiles=macro_profiles,
            keywords_by_pf=kw_by_pf,
        )

    writer.open_phase("processo-cluster")
    try:
        writer.execute_template(
            "clear_categoria_processo",
            CLEAR_CATEGORIA_PROCESSO_CYPHER,
            {}, phase="processo-cluster",
        )

        category_rows: list[dict[str, Any]] = []
        ts = now_iso()
        for desc in catalog.macro_clusters:
            cid = category_id(run_id, "macro", desc.macro_label)
            naming = cluster_names.get(cid) or {}
            category_rows.append({
                "id": cid,
                "nome": naming.get("nome") or f"Macro #{desc.macro_label}",
                "descricao": naming.get("descricao") or "",
                "marcadores": naming.get("marcadores") or [],
                "nivel": "macro",
                "n_processos": len(desc.member_protocolos),
                "centroid": desc.centroid.tolist(),
                "computed_at": ts,
            })
        for desc in catalog.micro_clusters:
            cid = category_id(run_id, desc.nivel, desc.micro_label, desc.macro_label)
            naming = cluster_names.get(cid) or {}
            category_rows.append({
                "id": cid,
                "nome": naming.get("nome") or f"{desc.nivel} #{desc.macro_label}.{desc.micro_label}",
                "descricao": naming.get("descricao") or "",
                "marcadores": naming.get("marcadores") or [],
                "nivel": desc.nivel,
                "n_processos": len(desc.member_protocolos),
                "centroid": desc.centroid.tolist(),
                "computed_at": ts,
            })
        if category_rows:
            for i in range(0, len(category_rows), 200):
                writer.execute_template(
                    "load_categoria_processo",
                    LOAD_CATEGORIA_PROCESSO_CYPHER,
                    {"rows": category_rows[i:i + 200]},
                    phase="processo-cluster",
                )

        sub_rows: list[dict[str, str]] = []
        for desc in catalog.micro_clusters:
            if desc.macro_label == NOISE_LABEL:
                continue
            sub_rows.append({
                "child_id": category_id(run_id, "micro", desc.micro_label, desc.macro_label),
                "parent_id": category_id(run_id, "macro", desc.macro_label),
            })
        if sub_rows:
            for i in range(0, len(sub_rows), 200):
                writer.execute_template(
                    "load_subcategoria_de",
                    LOAD_SUBCATEGORIA_DE_CYPHER,
                    {"rows": sub_rows[i:i + 200]},
                    phase="processo-cluster",
                )

        cat_rows: list[dict[str, Any]] = []
        for pf, a in catalog.assignments.items():
            if a.macro_label != NOISE_LABEL:
                cat_rows.append({
                    "protocolo_formatado": pf,
                    "categoria_id": category_id(run_id, "macro", a.macro_label),
                    "nivel": "macro",
                    "reclassificada": False,
                    "confidence": a.macro_strength,
                    "computed_at": ts,
                })
            if a.micro_label != NOISE_LABEL:
                nivel = "reclassificada" if a.reclassificada else "micro"
                cat_rows.append({
                    "protocolo_formatado": pf,
                    "categoria_id": category_id(run_id, nivel, a.micro_label, a.macro_label),
                    "nivel": nivel,
                    "reclassificada": a.reclassificada,
                    "confidence": a.micro_strength,
                    "computed_at": ts,
                })
        for i in range(0, len(cat_rows), 500):
            writer.execute_template(
                "load_categorizado_como",
                LOAD_CATEGORIZADO_COMO_CYPHER,
                {"rows": cat_rows[i:i + 500]},
                phase="processo-cluster",
            )

        if ctx.mode == "neo4j":
            writer.execute_template(
                "load_clustering_run",
                LOAD_CLUSTERING_RUN_CYPHER,
                {
                    "run_id": run_id,
                    "algo": "hdbscan",
                    "dbcv": dbcv_macro,
                    "silhouette": macro_silhouette,
                    "noise_ratio": macro_noise_ratio,
                    "n_macro": n_macro,
                    "n_micro": n_micro,
                    "n_processos": len(protocolos),
                    "computed_at": ts,
                },
                phase="processo-cluster",
            )
    finally:
        writer.close_phase("processo-cluster")

    exported = _export_catalog_artifacts(driver, run_id, protocolos, macro_labels)

    summary = {
        "run_id": run_id,
        "catalog_artifacts": exported,
        "total_processos": len(protocolos),
        "macro_clusters": n_macro,
        "macro_clusters_before_dedup": n_macro_raw,
        "macro_dedup_threshold": macro_dedup_threshold,
        "macro_outliers": n_macro_outliers,
        "micro_clusters": n_micro,
        "reclassificados": n_rescued,
        "dbcv_macro": dbcv_macro,
        "categorias_criadas": len(category_rows),
        "edges_criadas": len(cat_rows),
    }
    ctx.cache["processo_cluster_summary"] = summary
    log.info("processo-cluster complete: %s", summary)
