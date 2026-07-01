from __future__ import annotations

from collectors.live_collect import collect_all
from processing.clean import prepare_master_data
from processing.chunk import create_chunks
from rag.vector_store import build_vector_store


def main() -> None:
    print("Step 1/4: Collecting live data")
    collect_all()
    print("\nStep 2/4: Cleaning and normalizing data")
    prepare_master_data()
    print("\nStep 3/4: Creating sentence-aware chunks")
    create_chunks()
    print("\nStep 4/4: Building ChromaDB vector store")
    build_vector_store(reset=True)
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
