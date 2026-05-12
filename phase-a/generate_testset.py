from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lab24_core.csv_utils import write_csv
from lab24_core.env import load_env, require_env
from lab24_core.paths import DOCS_DIR, PHASE_A
from lab24_core.simple_rag import build_chunks, extractive_answer


def generate_with_ragas(size: int, output: Path, model: str, max_workers: int) -> None:
    load_env()
    require_env("OPENAI_API_KEY")

    try:
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas.run_config import RunConfig
        from ragas.testset import TestsetGenerator
        from ragas.testset.synthesizers.multi_hop.abstract import MultiHopAbstractQuerySynthesizer
        from ragas.testset.synthesizers.multi_hop.specific import MultiHopSpecificQuerySynthesizer
        from ragas.testset.synthesizers.single_hop.specific import SingleHopSpecificQuerySynthesizer
    except ImportError as exc:
        raise RuntimeError(f"Missing dependency for RAGAS testset generation: {exc}") from exc

    loader = DirectoryLoader(
        str(DOCS_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()
    if not documents:
        raise RuntimeError(f"No documents loaded from {DOCS_DIR}")

    generator = TestsetGenerator.from_langchain(
        llm=ChatOpenAI(model=model, temperature=0),
        embedding_model=OpenAIEmbeddings(),
    )
    query_distribution = [
        (SingleHopSpecificQuerySynthesizer(llm=generator.llm), 0.50),
        (MultiHopAbstractQuerySynthesizer(llm=generator.llm), 0.25),
        (MultiHopSpecificQuerySynthesizer(llm=generator.llm), 0.25),
    ]

    testset = generator.generate_with_langchain_docs(
        documents=documents,
        testset_size=size,
        query_distribution=query_distribution,
        run_config=RunConfig(max_workers=max_workers, timeout=240, max_retries=6, max_wait=30),
    )
    df = testset.to_pandas()
    df = normalize_ragas_columns(df)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"[OK] Saved RAGAS test set to {output}")
    if "evolution_type" in df:
        print(df["evolution_type"].value_counts())


def normalize_ragas_columns(df):
    """Normalize RAGAS 0.4 testset columns to the lab rubric names."""
    rename_map = {}
    if "user_input" in df.columns and "question" not in df.columns:
        rename_map["user_input"] = "question"
    if "reference" in df.columns and "ground_truth" not in df.columns:
        rename_map["reference"] = "ground_truth"
    if "reference_contexts" in df.columns and "contexts" not in df.columns:
        rename_map["reference_contexts"] = "contexts"
    if "synthesizer_name" in df.columns and "evolution_type" not in df.columns:
        rename_map["synthesizer_name"] = "evolution_type"
    df = df.rename(columns=rename_map)
    if "evolution_type" in df.columns:
        df["evolution_type"] = df["evolution_type"].replace(
            {
                "single_hop_specific_query_synthesizer": "simple",
                "multi_hop_abstract_query_synthesizer": "reasoning",
                "multi_hop_specific_query_synthesizer": "multi_context",
            }
        )
    return df


def generate_offline_template(size: int, output: Path) -> None:
    """Create a real corpus-derived draft when API/RAGAS is unavailable.

    This is a convenience draft for review, not a replacement for the RAGAS
    synthetic generator required by the rubric.
    """
    chunks = build_chunks(DOCS_DIR)
    if len(chunks) < 3:
        raise RuntimeError("Need at least 3 chunks to create an offline template.")

    rows = []
    plan = (
        ["simple"] * int(size * 0.5)
        + ["reasoning"] * int(size * 0.25)
        + ["multi_context"] * (size - int(size * 0.75))
    )
    for idx, evolution_type in enumerate(plan):
        chunk = chunks[idx % len(chunks)]
        if evolution_type == "simple":
            question = f"Tai lieu {chunk.source} noi gi ve noi dung chinh cua doan {chunk.index + 1}?"
            contexts = [chunk.text]
        elif evolution_type == "reasoning":
            question = f"Hay suy luan diem quan trong nhat tu doan {chunk.index + 1} trong {chunk.source}."
            contexts = [chunk.text]
        else:
            other = chunks[(idx + 7) % len(chunks)]
            question = f"So sanh thong tin lien quan giua {chunk.source} va {other.source}."
            contexts = [chunk.text, other.text]
        rows.append(
            {
                "question": question,
                "ground_truth": extractive_answer(question, contexts),
                "contexts": contexts,
                "evolution_type": evolution_type,
                "source": "offline_template_needs_manual_review",
            }
        )
    write_csv(output, rows, ["question", "ground_truth", "contexts", "evolution_type", "source"])
    print(f"[OK] Saved offline draft test set to {output}")
    print("[WARN] This draft is not a substitute for RAGAS generation in final submission.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=50)
    parser.add_argument("--output", type=Path, default=PHASE_A / "testset_v1.csv")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--offline-template", action="store_true")
    args = parser.parse_args()

    if args.offline_template:
        generate_offline_template(args.size, args.output)
    else:
        generate_with_ragas(args.size, args.output, args.model, args.max_workers)


if __name__ == "__main__":
    main()
