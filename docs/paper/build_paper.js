// Build the Bolt CFP submission as a Word document.
// Run: node docs/paper/build_paper.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, ImageRun, PageBreak, PageNumber, Header, Footer,
  TableOfContents, ExternalHyperlink, VerticalAlign,
} = require("docx");

const FIG = path.join(__dirname, "figures");
const OUT = path.join(__dirname, "Bolt_CFP_Submission.docx");

// ---- palette ----
const NAVY = "1E3A5F";
const ORANGE = "C0561F";
const GREY = "6B7280";
const HDR = "D5E8F0";
const HDR2 = "FFE3D6";
const LGREY = "F2F4F7";

// ---- helpers ----
const P = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, line: 276, ...(opts.before ? { before: opts.before } : {}) },
    alignment: opts.align,
    children: [new TextRun({ text, ...opts })],
  });

// paragraph from an array of TextRun specs (for inline bold/italic)
const RP = (runs, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 120, line: 276 },
    alignment: opts.align,
    children: runs.map((r) => (typeof r === "string" ? new TextRun(r) : new TextRun(r))),
  });

const H1 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
const H2 = (text) =>
  new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });

const bullet = (text, runs) =>
  new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 268 },
    children: runs ? runs.map((r) => new TextRun(r)) : [new TextRun(text)],
  });

const num = (text, runs) =>
  new Paragraph({
    numbering: { reference: "nums", level: 0 },
    spacing: { after: 80, line: 268 },
    children: runs ? runs.map((r) => new TextRun(r)) : [new TextRun(text)],
  });

function fig(file, w) {
  const dims = {
    "fig1_topology.png": [1827, 2092],
    "fig2_architecture.png": [3082, 1815],
    "fig3_pipeline.png": [2478, 1399],
    "fig4_hitl.png": [2478, 1215],
  }[file];
  const h = Math.round((w * dims[1]) / dims[0]);
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 160 },
    children: [
      new ImageRun({
        type: "png",
        data: fs.readFileSync(path.join(FIG, file)),
        transformation: { width: w, height: h },
        altText: { title: file, description: file, name: file },
      }),
    ],
  });
}

// ---- table builder ----
const CELL_BORDER = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const CELL_BORDERS = { top: CELL_BORDER, bottom: CELL_BORDER, left: CELL_BORDER, right: CELL_BORDER };

function cell(text, w, { fill, bold, italics, color, align, size } = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    borders: CELL_BORDERS,
    width: { size: w, type: WidthType.DXA },
    shading: fill ? { fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    verticalAlign: VerticalAlign.CENTER,
    children: lines.map(
      (ln) =>
        new Paragraph({
          alignment: align,
          spacing: { after: 0, line: 252 },
          children: [new TextRun({ text: ln, bold, italics, color, size: size ?? 18 })],
        })
    ),
  });
}

function table(widths, headerCells, rows, headerFill = HDR) {
  const total = widths.reduce((a, b) => a + b, 0);
  const headRow = new TableRow({
    tableHeader: true,
    children: headerCells.map((t, i) =>
      cell(t, widths[i], { fill: headerFill, bold: true, color: NAVY, size: 18 })
    ),
  });
  const bodyRows = rows.map(
    (r) =>
      new TableRow({
        children: r.map((c, i) => {
          const spec = typeof c === "object" && c.text !== undefined ? c : { text: c };
          return cell(spec.text, widths[i], { fill: spec.fill, bold: spec.bold, italics: spec.italics, color: spec.color, align: spec.align, size: 18 });
        }),
      })
  );
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [headRow, ...bodyRows],
  });
}

function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200, before: 40 },
    children: [new TextRun({ text, italics: true, size: 18, color: GREY })],
  });
}

// =====================================================================
//  DOCUMENT
// =====================================================================
const CW = 9360; // content width DXA (US Letter, 1in margins)

const titleBlock = [
  new Paragraph({ spacing: { before: 400, after: 0 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 60 },
    children: [new TextRun({ text: "Bolt: A Human-in-the-Loop Agentic AI System for", bold: true, size: 36, color: NAVY })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 220 },
    children: [new TextRun({ text: "Continuous Controls Testing in Auditing", bold: true, size: 36, color: NAVY })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 300 },
    children: [new TextRun({ text: "The auditor reaches the opinion. Bolt does the legwork to get them there.", italics: true, size: 22, color: ORANGE })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
    children: [new TextRun({ text: "[ Author Name(s) ]   ·   [ Affiliation ]   ·   [ Email ]", size: 20, color: GREY })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 300 },
    children: [new TextRun({ text: "Design Science Research Submission", size: 20, color: GREY })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 20 },
    children: [new TextRun({ text: "3rd International Conference on Auditing and Artificial Intelligence", bold: true, size: 22 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 20 },
    children: [new TextRun({ text: "University of Duisburg-Essen, Germany  ·  September 2–4, 2026", size: 20 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 320 },
    children: [new TextRun({ text: "Special Track: WCARS Collaboration (Rutgers CARLAB) — Continuous Auditing", italics: true, size: 19, color: GREY })],
  }),
];

// Abstract box (as a single-cell shaded table)
const abstractBox = new Table({
  width: { size: CW, type: WidthType.DXA },
  columnWidths: [CW],
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders: {
            top: { style: BorderStyle.SINGLE, size: 4, color: NAVY },
            bottom: { style: BorderStyle.SINGLE, size: 4, color: NAVY },
            left: { style: BorderStyle.SINGLE, size: 4, color: NAVY },
            right: { style: BorderStyle.SINGLE, size: 4, color: NAVY },
          },
          shading: { fill: LGREY, type: ShadingType.CLEAR },
          margins: { top: 140, bottom: 140, left: 200, right: 200 },
          width: { size: CW, type: WidthType.DXA },
          children: [
            new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Abstract", bold: true, size: 22, color: NAVY })] }),
            new Paragraph({
              spacing: { after: 120, line: 276 },
              children: [
                new TextRun({
                  text:
                    "Generative artificial intelligence is reshaping the audit profession, yet a central tension remains: how can autonomous systems accelerate fieldwork without displacing the professional judgment that audit assurance depends on? This paper presents Bolt, a design-science artifact that operationalizes continuous controls testing with a human auditor in the loop. Bolt is an agentic AI system built on a large language model orchestrated through a graph-based reasoning loop (plan → act → synthesize → draft). Given a single audit procedure — a test of controls or a substantive test tied to an objective and a financial-statement assertion — Bolt autonomously retrieves the in-scope population, tests every item against the relevant control criteria, grounds each finding in governing policy and audit-standard guidance via retrieval-augmented generation, consults prior-year workpapers for precedent, and drafts a structured workpaper for human review. ",
                  size: 19,
                }),
                new TextRun({
                  text:
                    "A core design invariant enforces auditability: no conclusion is admitted to a workpaper unless it traces to a retrieved criterion, and the system is constrained never to issue a final audit opinion. ",
                  size: 19,
                }),
                new TextRun({
                  text:
                    "We demonstrate Bolt on four reproducible audit procedures with deterministic planted deviations and evaluate it against four properties: functional correctness, criterion grounding, opinion-boundary guardrails, and reproducibility. We argue that the contribution is one of adaptation rather than replacement — the artifact expands the population an individual auditor can test while preserving the human sign-off.",
                  size: 19,
                }),
              ],
            }),
            new Paragraph({
              spacing: { after: 0 },
              children: [
                new TextRun({ text: "Keywords: ", bold: true, size: 19 }),
                new TextRun({ text: "agentic AI; autonomous audit agents; continuous auditing; retrieval-augmented generation; large language models; human-in-the-loop; design science; controls testing; audit automation.", size: 19, italics: true }),
              ],
            }),
          ],
        }),
      ],
    }),
  ],
});

// ---- body sections ----
const body = [];

// 1. Introduction
body.push(H1("1. Introduction"));
body.push(P("The integration of artificial intelligence (AI) into auditing is advancing from analytics and anomaly detection toward autonomous, tool-using agents that can plan and execute multi-step procedures. Large language models (LLMs) now reason over unstructured guidance, call external tools, and produce structured artifacts. For a profession whose output is assurance, this capability is double-edged: it promises to extend audit coverage from samples toward full populations, yet it raises acute questions about evidence sufficiency, traceability, bias, and the proper boundary between machine assistance and professional judgment."));
body.push(RP([
  "This paper responds to two of the conference's themes directly — ",
  { text: "agentic AI systems and autonomous audit agents", italics: true },
  ", and ",
  { text: "retrieval-augmented generation (RAG) for knowledge-based audit procedures", italics: true },
  " — and aligns with the WCARS continuous-auditing track. We present ",
  { text: "Bolt", bold: true },
  ", an artifact that treats the LLM agent as a staff auditor performing fieldwork and the human as the engagement lead who exercises judgment and signs off.",
]));
body.push(RP([
  { text: "Research question. ", bold: true },
  "How can an autonomous LLM agent perform audit procedures across a full population while preserving the auditability and human-judgment boundaries that professional assurance requires?",
]));
body.push(RP([
  { text: "Contribution. ", bold: true },
  "We make three contributions. First, we present a reference architecture for an autonomous audit agent that couples a graph-based reasoning loop with a modular tool layer and a retrieval-grounded criteria corpus. Second, we introduce two enforced design invariants — ",
  { text: "criterion grounding", italics: true },
  " (no conclusion without a cited criterion) and an ",
  { text: "opinion boundary", italics: true },
  " (the agent drafts but never concludes) — and show how each is operationalized in the prompt and validated in code. Third, we provide a reproducible demonstration and a property-based evaluation that the wider community can inspect and extend.",
]));

// 2. Background
body.push(H1("2. Background and Related Work"));
body.push(H2("2.1 Continuous auditing and full-population testing"));
body.push(RP([
  "Continuous auditing — the idea that assurance procedures can be performed on a near-real-time, automated basis — has a long lineage in the accounting-information-systems literature (Vasarhelyi & Halper, 1991; Alles, Kogan & Vasarhelyi, 2008). Subsequent work positioned big-data analytics and AI as the enabling technologies for moving from periodic sampling toward continuous, full-population monitoring (Appelbaum, Kogan & Vasarhelyi, 2017; Issa, Sun & Vasarhelyi, 2016). Bolt sits squarely in this tradition: it executes a procedure across the entire in-scope population rather than a judgmental sample, and it is designed to be re-run on a cadence.",
]));
body.push(H2("2.2 AI and automation in the audit profession"));
body.push(P("Kokina and Davenport (2017) characterize the trajectory of AI in auditing as one of progressive task automation rather than wholesale replacement, with professional judgment remaining the differentiator. This framing — adaptation, not replacement — is the normative stance Bolt adopts and enforces architecturally."));
body.push(H2("2.3 Agentic AI and the reason-act paradigm"));
body.push(P("Modern LLM agents interleave natural-language reasoning with tool invocation. The ReAct paradigm (Yao et al., 2023) demonstrated that alternating reasoning traces and actions improves reliability on knowledge-intensive tasks, while chain-of-thought prompting (Wei et al., 2022) established that explicit intermediate reasoning improves complex problem solving. Bolt implements a ReAct-style loop with an explicit sufficiency check that bounds the number of action rounds, making the agent's evidence-gathering both inspectable and terminating."));
body.push(H2("2.4 Retrieval-augmented generation for grounding"));
body.push(P("Retrieval-augmented generation (Lewis et al., 2020) conditions an LLM's output on documents retrieved from an external corpus, reducing unsupported generation and enabling citation. In an audit setting, grounding is not a convenience but a requirement: a finding that cannot be tied to a control criterion or standard is not audit evidence. Bolt therefore makes retrieval the gating step for every conclusion."));
body.push(H2("2.5 Research gap"));
body.push(P("Prior work establishes the desirability of continuous, AI-assisted auditing and the technical building blocks (agents, RAG) in isolation. What remains underexplored is a concrete, inspectable architecture that composes these blocks specifically for audit procedures while encoding the profession's guardrails — traceable evidence and a preserved human opinion — as enforced system properties rather than aspirations. Bolt addresses this gap as a design-science artifact."));

// 3. Method
body.push(H1("3. Research Method"));
body.push(RP([
  "We adopt the design-science research (DSR) paradigm (Hevner et al., 2004) and follow the DSR methodology process model of Peffers et al. (2007): problem identification, objective definition, design and development, demonstration, and evaluation. The artifact is the unit of contribution. Our design objectives, derived from the problem in Section 1, are:",
]));
body.push(num(null, ["DO1 — Autonomy: execute a complete audit procedure end-to-end from a single structured input."]));
body.push(num(null, ["DO2 — Coverage: test the full in-scope population, not a judgmental sample."]));
body.push(num(null, ["DO3 — Traceability: ground every conclusion in a retrievable, citable criterion."]));
body.push(num(null, ["DO4 — Boundary preservation: never issue a final audit opinion; draft for human sign-off."]));
body.push(num(null, ["DO5 — Reproducibility: produce deterministic, inspectable results suitable for demonstration and audit-trail review."]));
body.push(P("Sections 4–5 describe the design and demonstration; Section 6 evaluates the artifact against DO1–DO5.", { after: 160 }));

// 4. Artifact design
body.push(H1("4. Artifact Design"));
body.push(H2("4.1 Design overview"));
body.push(P("Bolt enforces a strict separation between evidence-gathering, which is automated, and opinion-forming, which is human. The auditor selects a procedure; the agent performs the fieldwork in seconds and returns a structured workpaper; the auditor exercises judgment on the exceptions and signs. Figure 4 summarizes this division of labour."));
body.push(RP([
  { text: "Technology stack. ", bold: true },
  "Bolt uses an LLM (Anthropic Claude) accessed through a LangChain integration; a graph-based agent runtime (LangGraph) implementing the StateGraph and reasoning loop; a tool layer exposed over the Model Context Protocol (MCP; Anthropic, 2024) with each tool server running as an independent process; a local persistent vector store (ChromaDB) for retrieval; and a Streamlit interface for the live demonstration. All data are synthetic; no real personal or financial information is used.",
]));

body.push(H2("4.2 Agent topology"));
body.push(P("Bolt is implemented as a graph-structured, ReAct-style loop (Figure 1). A procedure payload — objective, financial-statement assertion, control identifier, and population scope — enters the graph and flows through four node types:"));
body.push(bullet(null, ["PLAN — the agent decides which population to pull, which criteria are relevant, and what would constitute a deviation."]));
body.push(bullet(null, ["ACT — the agent calls tools (Section 4.3) to pull the population, run the control test, optionally sample, retrieve criteria, and retrieve precedent. A sufficiency check after each round decides whether more evidence is needed, with a hard cap of three rounds to guarantee termination."]));
body.push(bullet(null, ["SYNTHESIZE — the agent cross-references deviations against retrieved criteria and prior-year precedent, and assesses the deviation rate."]));
body.push(bullet(null, ["DRAFT WORKPAPER — the agent emits a structured JSON workpaper, which is then validated in code before display."]));
body.push(fig("fig1_topology.png", 318));
body.push(caption("Figure 1. The Bolt agent topology: a bounded ReAct loop terminating in a human sign-off."));
body.push(RP([
  "Agent state is carried in a typed structure with custom reducers so that evidence accumulates across action rounds without duplication. Two fields illustrate the design: a ",
  { text: "tool_calls", italics: true },
  " list that grows by append, and an ",
  { text: "evidence", italics: true },
  " dictionary merged by a custom reducer that de-duplicates lists and deep-merges nested results, preventing the same retrieved chunk or tested item from being counted twice.",
]));

body.push(H2("4.3 Tool layer: four MCP servers"));
body.push(P("Bolt's capabilities are exposed as four independent tool servers communicating with the agent over stdio (Figure 2). Decoupling tools as separate processes mirrors a separation-of-duties principle: the reasoning agent cannot silently alter the data or the criteria it is testing against."));
body.push(fig("fig2_architecture.png", 540));
body.push(caption("Figure 2. System architecture — the agent, four MCP tool servers, and their backing data sources."));
body.push(table(
  [2200, 3400, 3760],
  ["MCP server", "Tools exposed", "Role"],
  [
    ["ledger_db", "get_population, test_items_against_control, sample_population", "Retrieves the in-scope population and runs the deterministic deviation test; supports attribute and monetary-unit sampling."],
    ["evidence_registry", "get_master_record, check_authority_matrix", "Supplies vendor/employee master data and tests delegated approval authority — a key control signal."],
    [{ text: "criteria_rag ★", bold: true, fill: HDR2 }, { text: "query_criteria (policy | standard | all)", fill: HDR2 }, { text: "The grounding layer: semantic search over control policies and synthetic audit-standard summaries. Every conclusion must cite a result from here.", fill: HDR2 }],
    ["workpaper_rag", "query_prior_workpapers", "Returns prior-year workpapers for precedent, calibrating severity and flagging recurring findings."],
  ]
));
body.push(caption("Table 1. The four MCP tool servers and their responsibilities."));

body.push(H2("4.4 Criterion grounding and the RAG pipeline"));
body.push(RP([
  { text: "criteria_rag", italics: true },
  " is the critical server: it enforces design objective DO3. It indexes two corpora into a persistent vector store (Figure 3): four internal control policies (28 chunks) and three synthetic audit-standard summaries (15 chunks), for 43 retrievable chunks in total. Policies are chunked at section boundaries to preserve clause-level granularity; standard summaries carry additional assertion and objective metadata tags to enable filtered retrieval (for example, retrieving only material relevant to the Occurrence assertion).",
]));
body.push(fig("fig3_pipeline.png", 540));
body.push(caption("Figure 3. Ingestion and retrieval pipeline. Criteria and prior workpapers are embedded into vector collections; transactional and master data are read directly."));
body.push(RP([
  { text: "Copyright-clean corpus. ", bold: true },
  "To keep the artifact shareable, the standards corpus contains no verbatim text from published standards. Each file is an original, clearly labelled paraphrase of a concept (for example, control operating-effectiveness testing; the financial-statement assertions of occurrence, completeness, authorization, accuracy, and cutoff; sufficient appropriate audit evidence; and tolerable deviation rate). This is a deliberate design choice that lets the system be demonstrated and distributed without reproducing proprietary standard text.",
]));

body.push(H2("4.5 Workpaper output schema"));
body.push(P("Bolt always emits the same structured workpaper. Two fields encode the guardrails. The preliminary_conclusion describes findings and is constrained never to assert a final opinion (no “control is effective,” no “financials are fairly stated”). The recommended_disposition must end with the literal phrase “— Auditor judgment required”; this is instructed in the prompt and re-validated in code, which appends the suffix if the model omits it."));
body.push(table(
  [2700, 1500, 5160],
  ["Field", "Type", "Constraint / purpose"],
  [
    ["objective", "string", "What the procedure tests"],
    ["assertion", "string", "e.g. Authorization, Occurrence, Completeness"],
    ["control_id", "string", "Control under test"],
    ["procedure_performed", "string", "What Bolt did, in audit language"],
    ["population_summary", "string", "Source, period, size, total value"],
    ["sample", "string", "Items selected and method, or ‘full population’"],
    ["exceptions", "list", "Item ref + nature of deviation + criterion breached"],
    ["deviation_rate", "string", "e.g. ‘2 of 9 items (22.2%)’"],
    [{ text: "criteria_cited", bold: true, fill: HDR2 }, { text: "list", fill: HDR2 }, { text: "Must be non-empty — enforces criterion grounding (DO3)", fill: HDR2 }],
    ["prior_year_reference", "list", "Prior WP ref + conclusion + recurrence note"],
    [{ text: "preliminary_conclusion", bold: true, fill: HDR2 }, { text: "string", fill: HDR2 }, { text: "Describes findings; never a final opinion (DO4)", fill: HDR2 }],
    ["judgment_note", "string", "What the auditor must decide that Bolt cannot"],
    [{ text: "recommended_disposition", bold: true, fill: HDR2 }, { text: "string", fill: HDR2 }, { text: "NO EXCEPTION | DEFICIENCY NOTED | ESCALATE; must end ‘— Auditor judgment required’ (DO4)", fill: HDR2 }],
    ["prepared_at", "string", "ISO timestamp"],
  ]
));
body.push(caption("Table 2. The structured workpaper schema. Shaded rows carry enforced design invariants."));

body.push(H2("4.6 Human-in-the-loop division of labour"));
body.push(P("Figure 4 makes the artifact's normative claim concrete. Everything to the left is mechanizable legwork; everything to the right requires professional skepticism and judgment. Bolt is deliberately built so that the hand-off point — the signed workpaper — cannot be skipped."));
body.push(fig("fig4_hitl.png", 540));
body.push(caption("Figure 4. The division of labour between the agent and the auditor."));

// 5. Demonstration
body.push(H1("5. Demonstration"));
body.push(P("We demonstrate Bolt on four pre-built procedures spanning tests of controls and a substantive test. Each procedure runs against a synthetic population of 25 transactions across ten vendors, with planted deviations that make outcomes deterministic and reproducible on stage. Table 3 summarizes the procedures and their expected dispositions."));
body.push(table(
  [1500, 2600, 3360, 1900],
  ["Control", "Test", "Planted deviation(s)", "Expected disposition"],
  [
    ["CTRL-01", "Tests of controls — purchase-order approval authority (every PO ≥ $10,000 must carry valid manual approval by an authorized approver)", "TXN-003 ($45,000) approver authority exceeded; TXN-004 ($12,500) auto-approved above threshold", { text: "DEFICIENCY NOTED", bold: true, color: "9A6A00" }],
    ["CTRL-02", "Tests of controls — segregation of duties (no single person both requests and approves)", "TXN-011 requestor = approver (E-211)", { text: "DEFICIENCY NOTED", bold: true, color: "9A6A00" }],
    ["CTRL-03", "Substantive test — accounts-payable occurrence/authorization (vouch to support, scan duplicates)", "TXN-016 missing supporting document; TXN-019 duplicate invoice ($45,000)", { text: "ESCALATE", bold: true, color: "B0271E" }],
    ["CTRL-04", "Tests of controls — journal-entry review (clean control)", "None", { text: "NO EXCEPTION", bold: true, color: "1E7A45" }],
  ]
));
body.push(caption("Table 3. The four demonstration procedures with deterministic planted deviations."));
body.push(RP([
  "The clean procedure (CTRL-04) is included deliberately: it demonstrates that Bolt does not flag everything, returning ",
  { text: "NO EXCEPTION", bold: true },
  " when the control operates effectively. This guards against the failure mode in which an over-eager agent manufactures findings. A worked grounding example: for TXN-003, Bolt retrieves the delegated-authority clause from the purchase-order policy, compares the $45,000 invoice against approver E-302's $25,000 limit, records the exception with the breached clause cited, and consults prior-year precedent before drafting — but leaves the severity call to the auditor.",
]));

// 6. Evaluation
body.push(H1("6. Evaluation"));
body.push(P("We evaluate Bolt against the five design objectives using property-based criteria that can be checked automatically. An automated test suite asserts the structural and guardrail properties across all cached procedure runs."));
body.push(table(
  [1500, 2600, 5260],
  ["Objective", "Evaluation property", "Result"],
  [
    ["DO1 Autonomy", "Each procedure completes plan→act→synthesize→workpaper from one input without human intervention", "Met — all four procedures complete end-to-end"],
    ["DO2 Coverage", "The control test runs over the full 25-item population, not a sample", "Met — full-population testing with deviation rate reported"],
    ["DO3 Traceability", "criteria_cited is non-empty for every workpaper", "Met — asserted by the test suite for all runs"],
    ["DO4 Boundary", "preliminary_conclusion contains no final-opinion phrasing; recommended_disposition ends with the required suffix", "Met — prompt-enforced and code-validated; asserted in tests"],
    ["DO5 Reproducibility", "Planted deviations yield the same dispositions on every run; CTRL-01 surfaces TXN-003 and TXN-004; CTRL-04 yields zero exceptions", "Met — deterministic outcomes asserted in tests"],
  ]
));
body.push(caption("Table 4. Evaluation of the artifact against the five design objectives."));
body.push(RP([
  { text: "Reliability provisions. ", bold: true },
  "Three mechanisms harden the demonstration. First, automatic retry with exponential backoff handles transient model-provider overload. Second, a JSON-parse fallback in the workpaper node preserves raw model output if structured parsing fails, so a malformed response never crashes the run. Third, a cached-result “demo mode” can serve pre-captured workpapers for all four procedures, allowing the system to be demonstrated even without live model access — an important property for a conference stage.",
]));

// 7. Discussion
body.push(H1("7. Discussion"));
body.push(H2("7.1 Implications for practice"));
body.push(P("Bolt illustrates a feasible near-term operating model for internal audit: the agent expands the population a single auditor can test from a judgmental sample toward the full set, while the auditor's effort shifts from manual tickmarking to evaluating exceptions. Because every line traces to a cited criterion, the resulting workpaper is reviewable and defensible. The architecture generalizes: adding a procedure requires adding population data, a policy document, and a procedure registration — the agent and tools are procedure-agnostic."));
body.push(H2("7.2 Implications for research"));
body.push(P("The two enforced invariants — criterion grounding and the opinion boundary — offer a transferable pattern for assurance-grade AI: encode professional guardrails as validated system properties rather than relying on model behaviour alone. This reframes a portion of “trustworthy AI in audit” from a purely behavioural question into an architectural one, which is more amenable to inspection and, potentially, to regulatory attestation."));
body.push(H2("7.3 Adaptation, not replacement"));
body.push(P("The artifact embodies the conference's recurring theme. Bolt is the staff auditor doing fieldwork at machine speed and scale; the human remains the engagement lead who exercises judgment and signs the workpaper. The sign-off is not a courtesy step bolted on at the end — it is the point the entire architecture is built to protect."));

// 8. Limitations
body.push(H1("8. Limitations and Future Work"));
body.push(bullet(null, ["Synthetic data. The demonstration uses synthetic transactions, masters, and paraphrased standards. Validation on real engagement data, under appropriate controls, is future work."]));
body.push(bullet(null, ["Deterministic deviations. Planted deviations ensure reproducibility but do not test the agent against the long tail of ambiguous real-world exceptions."]));
body.push(bullet(null, ["Single-procedure scope. Bolt currently runs one procedure on demand. A continuous deployment — scheduling, historical trend analysis across periods, and an expanding precedent base — is the natural next step and the clearest path to true continuous auditing."]));
body.push(bullet(null, ["Model dependence and bias. Outputs depend on the underlying LLM; systematic evaluation of bias, robustness to adversarial inputs, and explanation quality is needed before any assurance use."]));
body.push(bullet(null, ["No user study. We evaluate system properties, not auditor acceptance or decision quality. A behavioural study of auditors working with Bolt-drafted workpapers would strengthen the contribution."]));

// 9. Conclusion
body.push(H1("9. Conclusion"));
body.push(P("We presented Bolt, a human-in-the-loop agentic AI system for continuous controls testing. Bolt couples a bounded reason-act loop with a modular tool layer and a retrieval-grounded criteria corpus, and it encodes two of the audit profession's core guardrails — traceable evidence and a preserved human opinion — as enforced system properties. A reproducible demonstration over four procedures and a property-based evaluation show that the artifact meets its design objectives. The contribution is one of adaptation: Bolt does the legwork so the auditor can reach the opinion.", { after: 160 }));

// References
body.push(H1("References"));
body.push(new Paragraph({
  spacing: { after: 140 },
  children: [new TextRun({ text: "Note to author: the references below are well-established works provided as a starting scaffold. Verify every citation against the original source and the conference's required citation style, and add the specific literature your final argument relies on before submission.", italics: true, size: 18, color: ORANGE })],
}));

const refs = [
  "Alles, M. G., Kogan, A., & Vasarhelyi, M. A. (2008). Putting continuous auditing theory into practice: Lessons from two pilot implementations. Journal of Information Systems, 22(2), 195–214.",
  "Anthropic. (2024). Introducing the Model Context Protocol. Anthropic. https://www.anthropic.com/news/model-context-protocol",
  "Appelbaum, D., Kogan, A., & Vasarhelyi, M. A. (2017). Big data and analytics in the modern audit engagement: Research needs. Auditing: A Journal of Practice & Theory, 36(4), 1–27.",
  "Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). Design science in information systems research. MIS Quarterly, 28(1), 75–105.",
  "Issa, H., Sun, T., & Vasarhelyi, M. A. (2016). Research ideas for artificial intelligence in auditing: The formalization of audit and workforce supplementation. Journal of Emerging Technologies in Accounting, 13(2), 1–20.",
  "Kokina, J., & Davenport, T. H. (2017). The emergence of artificial intelligence: How automation is changing auditing. Journal of Emerging Technologies in Accounting, 14(1), 115–122.",
  "Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems, 33, 9459–9474.",
  "Peffers, K., Tuunanen, T., Rothenberg, M. A., & Chatterjee, S. (2007). A design science research methodology for information systems research. Journal of Management Information Systems, 24(3), 45–77.",
  "Vasarhelyi, M. A., & Halper, F. B. (1991). The continuous audit of online systems. Auditing: A Journal of Practice & Theory, 10(1), 110–125.",
  "Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., … Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. Advances in Neural Information Processing Systems, 35, 24824–24837.",
  "Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. International Conference on Learning Representations (ICLR).",
];
refs.forEach((r) =>
  body.push(new Paragraph({
    spacing: { after: 100, line: 268 },
    indent: { left: 360, hanging: 360 },
    children: [new TextRun({ text: r, size: 19 })],
  }))
);

// =====================================================================
const doc = new Document({
  creator: "Bolt",
  title: "Bolt: A Human-in-the-Loop Agentic AI System for Continuous Controls Testing in Auditing",
  styles: {
    default: { document: { run: { font: "Calibri", size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Calibri", color: NAVY },
        paragraph: { spacing: { before: 300, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Calibri", color: "2E4A6B" },
        paragraph: { spacing: { before: 180, after: 90 }, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
      { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              border: { top: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 6 } },
              children: [
                new TextRun({ text: "Bolt — ICAAI 2026 submission   ·   ", size: 16, color: GREY }),
                new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 16, color: GREY }),
              ],
            }),
          ],
        }),
      },
      children: [
        ...titleBlock,
        abstractBox,
        new Paragraph({ spacing: { after: 200 } }),
        new Paragraph({
          children: [new TextRun({ text: "Contents", bold: true, size: 24, color: NAVY })],
          spacing: { after: 100 },
        }),
        new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
        new Paragraph({ children: [new PageBreak()] }),
        ...body,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("Wrote", OUT, `(${buf.length.toLocaleString()} bytes)`);
});
