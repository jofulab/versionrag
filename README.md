<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/versionrag-logo-dark.svg">
    <img src="docs/assets/versionrag-logo.svg" alt="VersionRAG" width="520">
  </picture>
</p>

<p align="center">Version-aware retrieval-augmented generation for evolving documents</p>

<p align="center">
  <a href="https://arxiv.org/abs/2510.08109">Paper</a> ·
  <a href="https://huggingface.co/VersionRAG">Data</a> ·
  <a href="#citation">Citation</a>
</p>

This repository contains the reference implementation for our paper:

> **VersionRAG: Version-Aware Retrieval-Augmented Generation for Evolving Documents**<br>
> Linus Stuhlmann, Kajaluxan Mathitharan, Daniel Huwiler, Kurt Stockinger, Jonathan Fürst<br>
> *Findings of the Association for Computational Linguistics: EACL 2027*

## Install

Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker.

```bash
uv sync
cp .env.example .env     # OPENAI_API_KEY, NEO4J_USER, NEO4J_PASSWORD
docker compose up -d     # Neo4j + Qdrant
```

## Use

The system runs as an HTTP service.

```bash
make start   # Neo4j + Qdrant via docker compose, then the API on http://localhost:8000

# get a corpus, e.g. VersionQA-Software from Hugging Face
uvx --from huggingface_hub hf download VersionRAG/VersionQA-Software --repo-type dataset --local-dir data/software

curl -X POST localhost:8000/indexing/run -H 'Content-Type: application/json' \
     -d '{"data_dir": "data/software/corpus", "recursive": true, "reset": true}'
curl -X POST localhost:8000/query -H 'Content-Type: application/json' \
     -d '{"question": "What changed in Docker Compose 2.38.1?"}'
```

Interactive API documentation is at <http://localhost:8000/docs>.

## How it works

Indexing builds a typed graph over five node types: Category, Document, Version, Content and Change. `NEXT` edges carry the version order; Change nodes hold the diff between each consecutive
pair. Chunks live in Qdrant with `(document, version)` as filterable payload, the graph in Neo4j.

At query time a parser resolves the question to a `(document, version)` pair and an intent, and
the router picks a path:

| Intent | Path |
|---|---|
| Content retrieval | vector search filtered on `(document, version)` |
| Version listing | enumeration over Version nodes |
| Change retrieval | lookup in Change nodes for the version pair |

```
src/versionrag/
  indexing/     pipeline, graph builder, attribute and change extraction, diff filtering
  retrieval/    query parser, router, graph and vector retrievers, fusion
  generation/   answer generation and prompts
  clients/      Neo4j, Qdrant, LLM, embeddings, usage tracking
  models/       schemas and enums
```

## Datasets

- [VersionQA-Software](https://huggingface.co/datasets/VersionRAG/VersionQA-Software): 869 questions, 882 versions of open-source documentation
- [VersionQA-Legal](https://huggingface.co/datasets/VersionRAG/VersionQA-Legal): 547 questions, 355 versions of amended UK legislation

## Citation

If this repository is useful for your work, we would appreciate it if you cited our paper:

```bibtex
@inproceedings{stuhlmann2027versionrag,
  title     = {{VersionRAG}: Version-Aware Retrieval-Augmented Generation for Evolving Documents},
  author    = {Stuhlmann, Linus and Mathitharan, Kajaluxan and Huwiler, Daniel and
               Stockinger, Kurt and F{\"u}rst, Jonathan},
  booktitle = {Findings of the Association for Computational Linguistics: EACL 2027},
  year      = {2027}
}
```

## License

The code is released under the MIT License (see [LICENSE](LICENSE)). The datasets on Hugging Face
carry their own licences, listed in each dataset card.

## Contact

Jonathan Fürst, jonathan.fuerst@zhaw.ch
