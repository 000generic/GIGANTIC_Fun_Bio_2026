<!-- Last updated: 2026 May 25 — initial fill during documentation cleanup pass.
     This README is intentionally minimal; will be expanded as the cleanup
     progresses. -->

# GIGANTIC

**GIGANTIC** is a modular framework for AI-assisted comparative genomics and
phylogenomics. It is designed to be cloned from GitHub, copied into a renamed
project directory, and then operated through AI assistant sessions rooted at
that renamed project directory.

The mantra: **you guide AI - AI does the work!** GIGANTIC's
structure, conventions, and documentation are built around that model.

GIGANTIC use is built around a given project implemented through human-AI chat. It provides a framework of subprojects containing automated bioinformatic and phylogenetic workflows under the hood. It includes extensive documentation at every turn - READMEs for humans and AI_GUIDEs for AIs. For the non-expert user, it is intended as a wandering yet guided - often surprising & hopefully more fun than frustrating - research conversation to explore species, genomes, ideas, and data with an AI in chat. One where the human is guided and guides - and the AI acts. GIGANTIC floats you along in conversation - but with an exosuit grounded in sequence exploration - built to provide rigorous tools and methods in phylogenomics - and less excitingly but perhaps most critically - on-demand and behind the scenes documentation of chat as a record of research development and implementation, providing provenance in support of attribution, transparency, reproducibility, and publication. In this sense, a GIGANTIC project serves as a digital research notebook for comparative genomic and phylogenetic work - intended in the end to be archived and maintained no differently than a lab notebook at the bench.

Species for the demo are below - species set is species42. It is built for discovery of gene and genome evolution within a comparative framework of deuterostomes. It leverages deep functional knowledge in human, mouse and to a lesser extent zebrafish - and in the worm and fly models as outgroups. Hippo & splattering of cetaceans - plus octopus - fill things out. Entry requirements into species42 included a public high-quality annotated genome.

*Demo species set (species42, 42 species, deuterostome-focused):*

| Phylum | Species | Common name | Genome |
|--------|---------|-------------|--------|
| Chordata | *Homo sapiens* | human | [GCF_000001405.40](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000001405.40/) |
| Chordata | *Mus musculus* | house mouse | [GCF_000001635.27](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_000001635.27) |
| Chordata | *Danio rerio* | zebrafish | [GCF_049306965.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_049306965.1/) |
| Chordata | *Balaenoptera musculus* | blue whale | [GCF_009873245.2](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_009873245.2) |
| Chordata | *Megaptera novaeangliae* | humpback whale | [GCA_041834305.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_041834305.1/) |
| Chordata | *Balaenoptera borealis* | sei whale | [GCF_965194805.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_965194805.1) |
| Chordata | *Orcinus orca* | killer whale | [GCF_937001465.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_937001465.1) |
| Chordata | *Tursiops truncatus* | common bottlenose dolphin | [GCF_011762595.2](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_011762595.2) |
| Chordata | *Phocoena phocoena* | harbor porpoise | [GCF_963924675.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_963924675.1) |
| Chordata | *Hippopotamus amphibius kiboko* | hippo | [GCF_030028045.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_030028045.1) |
| Chordata (Cephalochordata) | *Branchiostoma floridae* | Floridian lancelet | [GCF_000003815.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000003815.2/) |
| Chordata (Cephalochordata) | *Branchiostoma lanceolatum* | Mediterranean amphioxus | [GCF_035083965.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_035083965.1/) |
| Chordata (Urochordata) | *Ascidia mentula* | sea squirt | [GCF_947561715.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_947561715.1/) |
| Chordata (Urochordata) | *Botryllus schlosseri* | star tunicate | [GCF_051294905.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_051294905.1/) |
| Chordata (Urochordata) | *Corella eumyota* | orange-tipped sea squirt | [GCF_963082875.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_963082875.1/) |
| Chordata (Urochordata) | *Phallusia mammillata* | white sea squirt | [GCF_965637545.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_965637545.1/) |
| Chordata (Urochordata) | *Styela clava* | rough sea squirt | [GCF_964204865.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964204865.1/) |
| Chordata (Urochordata) | *Aplidium turbinatum* | colonial sea squirt | [GCF_918807975.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_918807975.1/) |
| Chordata (Urochordata) | *Ciona intestinalis* | vase tunicate | [GCF_018327825.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_018327825.1/) |
| Chordata (Urochordata) | *Clavelina lepadiformis* | light-bulb sea squirt | [GCF_947623445.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_947623445.1/) |
| Chordata (Urochordata) | *Oikopleura dioica* | larvacean | [GCF_907165135.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_907165135.1/) |
| Chordata (Urochordata) | *Thalia democratica* | salp | [GCF_965202585.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_965202585.1/) |
| Echinodermata | *Antedon bifida* | rosy feather star | [GCF_963402885.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_963402885.1/) |
| Echinodermata | *Asterias rubens* | European sea star | [GCF_902459465.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_902459465.1/) |
| Echinodermata | *Lytechinus pictus* | Cyclins Nobel Prize painted sea urchin | [GCF_037042905.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_037042905.1/) |
| Echinodermata | *Amphiura filiformis* | brittlestar | [GCF_039555335.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_039555335.1/) |
| Echinodermata | *Antedon mediterranea* | Mediterranean feather star | [GCF_964355755.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964355755.1/) |
| Echinodermata | *Apostichopus japonicus* | Japanese sea cucumber | [GCF_037975245.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_037975245.1/) |
| Echinodermata | *Asterias amurensis* | Northern Pacific sea star | [GCF_032118995.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_032118995.1/) |
| Echinodermata | *Diadema setosum* | long-spined sea urchin | [GCF_964275005.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964275005.2/) |
| Echinodermata | *Eupentacta fraudatrix* | sea cucumber | [GCA_056552365.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_056552365.1/) |
| Echinodermata | *Holothuria leucospilota* | black sea cucumber | [GCA_029531755.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_029531755.1/) |
| Echinodermata | *Lytechinus variegatus* | green sea urchin | [GCF_018143015.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_018143015.1/) |
| Echinodermata | *Mesocentrotus franciscanus* | red sea urchin | [GCA_037976565.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCA_037976565.1/) |
| Echinodermata | *Patiria miniata* | bat sea star | [GCF_015706575.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_015706575.1/) |
| Echinodermata | *Strongylocentrotus purpuratus* | purple sea urchin | [GCF_000002235.5](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000002235.5/) |
| Hemichordata | *Glandiceps talaboti* | enteropneust acorn worm | [GCF_964340395.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_964340395.1/) |
| Hemichordata | *Ptychodera flava* | enteropneust acorn worm | [GCF_041260155.1](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_041260155.1/) |
| Hemichordata | *Schizocardium californicum* | enteropneust acorn worm | [figshare:25816303](https://figshare.com/articles/dataset/Schizocardium_californicum/25816303) |
| Nematoda | *Caenorhabditis elegans* | roundworm | [GCF_000002985.6](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000002985.6/) |
| Arthropoda | *Drosophila melanogaster* | fruit fly | [GCF_000001215.4](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_000001215.4/) |
| Mollusca | *Octopus bimaculoides* | California two-spot octopus | [GCF_001194135.2](https://www.ncbi.nlm.nih.gov/datasets/genome//GCF_001194135.2/) |

---

## Getting started — three steps

### 1. Clone the repository

```
git clone https://github.com/000generic/GIGANTIC.git
```

### 2. Copy and rename the project template

`gigantic_project-COPYME/` (inside the cloned `GIGANTIC/`) is the project
template. Copy it to a working location **outside** the `GIGANTIC/` clone, and
**rename it** to something specific to your research project:

```
cp -r GIGANTIC/gigantic_project-COPYME /path/to/work/gigantic_project-cephalopod_evolution
```

**Project naming convention**: `gigantic_project-<your_project_name>`.
Examples:
- `gigantic_project-cephalopod_evolution`
- `gigantic_project-early_animal_phylogenomics`
- `gigantic_project-mollusc_neural_genes`

The renamed directory is now your project. It is self-contained: every input,
workflow, output, and documentation file lives inside it. You can archive the
whole directory as the complete record of your project.

### 3. Start a fresh, naive AI assistant session rooted at the renamed project

Open a new AI assistant session (Claude Code, Cursor, ChatGPT, Gemini, or
any other codebase-aware AI assistant) and **root it at the renamed project
directory**, not at the cloned `GIGANTIC/` directory.

For example, if you renamed your project to
`gigantic_project-cephalopod_evolution`, your AI session should treat that
directory as its working root.

**All subsequent project work happens through AI sessions rooted at your
renamed project directory.** The `GIGANTIC/` clone is the framework; your
renamed project directory is where you actually do science.

---

## Why this structure

- **`GIGANTIC/` is the framework that gets versioned on GitHub.** It ships;
  it doesn't run.
- **Your renamed project is what runs.** It is the canonical record of your
  research project — fully reproducible, fully archivable, fully separable
  from any other project that uses GIGANTIC.
- **AI sessions rooted at the renamed project** stay focused on your project
  scope and don't have to mentally subtract framework-development context
  from every response.

---

## Where to find more

- **Project template setup, conventions, and AI guidance**: inside
  `gigantic_project-COPYME/` — specifically `README.md`, `AI_GUIDE.md`, and
  `CLAUDE.md` in that directory. Their content travels with your renamed
  copy.
- **AI-assistant-facing guidance for the framework itself**:
  [`AI_GUIDE.md`](AI_GUIDE.md) in this directory.
- **Behavior and posture for research-grade work** (full documentation,
  transparency, archival, replication): see `CLAUDE.md` and `AI_BEHAVIOR.md`
  inside `gigantic_project-COPYME/` (these travel with each renamed project
  copy — research-grade posture belongs at the project level, not at the
  framework level).
- **Standard repository files**: [`LICENSE`](LICENSE),
  [`CITATION.cff`](CITATION.cff), [`CONTRIBUTING.md`](CONTRIBUTING.md),
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

---

*Detailed documentation of subprojects, workflows, conventions, and
AI-assistant behavior lives inside `gigantic_project-COPYME/` and travels
with each renamed project copy. This top-level README is intentionally a
minimal landing page.*
