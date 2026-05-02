# Prompt Size Reduction Plan

Baseline:
- Last pushed commit: `581be88`
- Current live prompts are still in `app.py`
- This file is a review draft only. No prompt reduction is merged yet.

## Goal

Reduce prompt size without losing:
- believable title and summary quality
- broader but clean skills
- grounded experience bullets
- JD alignment without history rewriting

The main rule:
- keep judgment in prompts
- move formatting and cleanup to code

---

## 1. Analysis Prompt

### Keep
- identify target role, core problem, system description
- derive core and supporting skills from the system
- do not keyword-match blindly
- do not invent unsupported domain expertise
- think in terms of resume emphasis

### Shrink
- ATS explanation can be shorter
- remove repeated “real reader is recruiter” language
- reduce the long derivation block into fewer lines

### Move to code
- none of the analysis logic should move much; this prompt still carries the most value

### Candidate shorter prompt
```text
You are a resume reconstruction engine.
Assume the candidate has 4+ years of experience.
Analyze the JD before any resume writing.
Infer the real engineering problem, target system, workflows, and hiring signals.
Do not mirror the JD or invent unsupported domain expertise.
Return only structured analysis matching the schema.

Extract:
- target_role
- core_problem
- system_description
- responsibilities
- workflows
- core_skills
- supporting_skills
- behavioral_signals
- gaps
- build_strategy

Derive supporting_skills from what is required to build, run, scale, monitor, secure, validate, and debug the system.
Distinguish essential requirements from supporting signals.
Make the analysis useful for tailoring by emphasis and ordering, not by rewriting history.
```

### Expected impact
- low risk
- moderate speed gain

---

## 2. Core Prompt: Title + Summary + Skills

### Keep
- natural title phrasing
- summary length and role-family awareness
- no overclaiming
- one-skill-per-item guidance
- broader skills plus JD-aligned stack
- expected skill pattern examples

### Shrink
- remove repeated “authentic, human, recruiter-readable” lines
- reduce ATS/tone block to 1-2 lines
- reduce skills philosophy text

### Move to code
- slash/bracket cleanup
- duplicate category merge
- skill ordering
- packed-item splitting
- char/length enforcement

### Candidate shorter prompt
```text
You are a resume reconstruction engine.
Build only Updated Title, Updated Summary, and Updated Skills.
Assume the candidate has 4+ years of experience.
Use the JD analysis as the source of truth.
Do not mirror the JD or invent unrealistic expertise.

TITLE:
- natural human job title
- 2-8 words
- preserve seniority when clearly signaled
- stay close to a clean JD title

SUMMARY:
- 65-95 words
- build from the core problem, target system, and strongest transferable evidence
- include systems, technologies, and problems solved
- adapt by role family: systems/reliability, backend ownership, or customer-facing integration
- align to the company domain without overclaiming direct domain depth

SKILLS:
- use only allowed categories
- exactly one category per line
- each item must be one short skill or capability
- no slashes, brackets, or qualifier text
- keep the primary JD-aligned stack visible
- include broader engineering capabilities shown by the work
- do not repeat the same concept across categories
- include only believable day-to-day skills
- expected pattern:
  - Programming Languages: Java, SQL, JavaScript
  - Backend Engineering: REST API design, Application logic, Object-oriented development
  - Testing & Quality: Unit testing, Integration testing, Debugging

Return only the final result matching the schema.
```

### Expected impact
- high speed gain
- low to medium quality risk

---

## 3. Experience Prompt

### Keep
- fixed company/date structure
- no historical title rewriting
- bullet formula
- believable metrics
- company anchor realism

### Shrink
- collapse originality/grounding rules
- remove repeated warnings about distributed-systems copy
- shorten project-story rule

### Move to code
- bullet count checks
- word count checks
- punctuation validation
- generic phrase detection
- title sanitization

### Candidate shorter prompt
```text
You are a resume reconstruction engine.
Build only the Professional Experience section.
Assume the candidate has 4+ years of experience.
Use the JD analysis and core resume sections as the source of truth.
Do not mirror the JD or invent unrealistic tools or expertise.

RULES:
- follow the fixed company, location, and date structure exactly
- keep historical titles believable
- do not rewrite titles just to match the target role
- each bullet must be 25-30 words
- recent roles should sell harder than older ones

BULLET FORMULA:
[Strong Verb] + [System built/optimized] + using [1-3 tools] + under [constraint or engineering decision] + resulting in [measurable impact].

Each bullet must include:
- real system context
- 1-3 tools
- a constraint or engineering decision
- a measurable metric

Keep each company as one coherent project story.
Tailor by emphasis, not by rewriting history.
Prefer believable metrics over suspicious precision.

Fixed experience blueprints:
- McKinsey & Company | CA, USA | May 2025 – Present | bullets: 6-7 | anchor: enterprise delivery, applied AI workflows, ingestion and retrieval systems, customer-facing software
- Uber | CA, USA | February 2024 – May 2025 | bullets: 5-6 | anchor: operational tooling, transaction validation, real-time workflows, internal product systems
- KPMG | India | September 2021 – July 2022 | bullets: 5 | anchor: audit and compliance systems, Java backend services, document processing, reporting workflows
- Trigent Software | India | March 2020 – August 2021 | bullets: 3 | anchor: frontend engineering, UI migration, responsive web delivery, QA-oriented implementation

Return only the final result matching the schema.
```

### Expected impact
- high speed gain
- medium quality risk if anchors are too compressed

---

## 4. Reachout Prompt

This one should stay separate from the resume prompts.

### Best strategy
- plain text output only
- tiny input
- hard 300-character check in code

### Candidate prompt
```text
Write one short LinkedIn reachout for a recruiter or hiring manager.
Keep it under 300 characters.
Use this shape:
Hey <name>, keeping this short:
<1 short background line>
<1 short fit line>
I am highly interested in this role. What can I do to get an interview? Thanks for your time!
Use only facts grounded in the provided JD and resume snapshot.
Do not invent companies, metrics, or domain expertise.
Return only the message text.
```

---

## Review Order

Recommended sequence:
1. analysis
2. core
3. experience
4. reachout

That order keeps the risky changes isolated and measurable.

---

## What to Measure After Each Merge

- response time
- truncation rate
- malformed output rate
- title realism
- summary sharpness
- skills cleanliness
- bullet believability

---

## Recommendation

Start by trimming:
- core prompt first
- then experience
- analysis last

Reason:
- core and experience are the main latency drivers
- analysis still carries the most reasoning value per token

---

## Core Prompt Review: V1

### What the core prompt is responsible for

The core prompt only needs to produce:
- title
- summary
- skills

It does **not** need to carry:
- full bullet-writing philosophy
- long ATS philosophy
- repeated humanization language
- formatting cleanup rules that code already handles

### What we must preserve

#### Title
- natural title phrasing
- preserve seniority
- stay close to clean JD titles
- do not turn tool names into titles

#### Summary
- 65-95 words
- role-family-aware
- grounded to transferable evidence
- no overclaiming direct domain expertise

#### Skills
- one skill per item
- one category per line
- no slash/bracket noise
- JD-aligned stack visible
- broader engineering capability retained
- no duplicate concepts
- clear expected pattern examples

### What we can safely remove from the live core prompt

- `This is a targeted fit document for recruiter first-scan clarity, not a full biography.`
- `Write naturally, specifically, and without keyword stuffing.`
- the longer repeated tone language
- repeated “human readability first” style lines
- extra restatements of “believable day-to-day skills”
- extra restatements of “do not overfill”

These are directionally useful, but they repeat ideas already enforced elsewhere.

### What code already covers well enough

- duplicate category handling
- packed skill splitting
- punctuation cleanup
- category ordering
- min category count
- malformed/meta skill rejection

That means the prompt can stop trying to be a formatter.

### Proposed Core Prompt V1

```text
You are a resume reconstruction engine.
Build only Updated Title, Updated Summary, and Updated Skills.
Assume the candidate has 4+ years of experience.
Use the JD analysis as the source of truth.
Do not mirror the JD or invent unrealistic expertise.

TITLE:
- natural human job title
- 2-8 words
- preserve seniority when clearly signaled
- reflect the role, not tool names
- stay close to a clean JD title

SUMMARY:
- 65-95 words
- build from the core problem, target system, and strongest transferable evidence
- include systems, technologies, and problems solved
- adapt by role family:
  - platform roles: systems, APIs, reliability, scale
  - backend delivery roles: ownership, architecture, execution
  - customer-facing solutions roles: integrations, troubleshooting, technical communication
- align to the company domain without overclaiming direct domain expertise

SKILLS:
- use only allowed categories
- exactly one category per line
- each item must be one short skill or capability
- no slashes, brackets, or qualifier text
- keep the primary JD-aligned stack visible
- include broader engineering capabilities shown by the work
- do not repeat the same concept across categories
- include only believable day-to-day skills
- expected pattern:
  - Programming Languages: Java, SQL, JavaScript
  - Backend Engineering: REST API design, Application logic, Object-oriented development
  - Testing & Quality: Unit testing, Integration testing, Debugging

Return only the final result matching the schema.
```

### Why this should still work

This version still keeps:
- role-family control
- title realism
- summary grounding
- skills shape
- expected output examples

But it drops:
- prompt philosophy repetition
- formatting instructions already enforced in code
- low-value tone duplication

### Expected outcome

Should improve:
- speed
- output focus
- skills consistency

May slightly increase risk of:
- more generic summaries

That is the main thing to watch in testing.

### Decisions locked from ATS/recruiter feedback

Keep:
- title stays close to the JD title when that title is already clean and appropriate
- skills section stays clearly aligned to JD-facing skills plus broader supporting skills

Do not carry into core prompt:
- job-search philosophy like mass apply / submit fast

Reason:
- that belongs to product flow and latency design
- not to title/summary/skills writing logic

---

## Experience Prompt Review: Direction

Based on the recruiter-style guidance, the experience prompt should keep or add:

### Keep
- bullets grounded in real work
- keywords integrated through real achievements
- title realism
- JD alignment by emphasis, not history rewriting

### Add
- first bullet under each company should be a very simple summary bullet
- the rest of the bullets should follow:
  - What = keyword / qualification
  - How = how it was used
  - Why = why it mattered

### Interpretation note

I am interpreting your note as:
- **toddler-simple summary bullet**

not literally “two-letter”.

So the first bullet should be:
- simpler
- easier to scan
- less dense than the rest

### Candidate experience prompt adjustment

Add something like:

```text
- The first bullet under each company is a simple summary bullet written in plain language.
- All later bullets should follow:
  - What: the keyword, skill, or qualification
  - How: how it was used
  - Why: why it mattered or what changed
```

### Why this helps

- more recruiter-readable
- faster first scan
- still ATS-compatible because keywords appear in context
- fits the “natural keyword integration” advice better than keyword stuffing

### Proposed Experience Prompt V1

```text
You are a resume reconstruction engine.
Build only the Professional Experience section.
Assume the candidate has 4+ years of experience.
Use the JD analysis and core resume sections as the source of truth.
Do not mirror the JD or invent unrealistic tools or expertise.
Tailor by emphasis, not by rewriting history.

RULES:
- follow the fixed company, location, and date structure exactly
- keep historical titles believable
- do not rewrite titles just to imitate the target role
- recent roles should sell harder than older ones
- each bullet must be 25-30 words

BULLET DESIGN:
- the first bullet under each company is a simple summary bullet in plain language
- all later bullets should follow:
  - What: the skill, keyword, or qualification
  - How: how it was used
  - Why: why it mattered or what changed

BULLET FORMULA:
[Strong Verb] + [System or workflow] + using [1-3 tools] + under [constraint or engineering decision] + resulting in [measurable impact].

Each bullet must include:
- real system or workflow context
- 1-3 tools or technical skills
- a constraint or engineering decision
- a measurable metric

Keep each company as one coherent project story.
Prefer believable metrics over suspicious precision.
Keep company sections realistic to their role family and time period.

Fixed experience blueprints:
- McKinsey & Company | CA, USA | May 2025 – Present | bullets: 6-7 | anchor: enterprise delivery, applied AI workflows, ingestion and retrieval systems, customer-facing software
- Uber | CA, USA | February 2024 – May 2025 | bullets: 5-6 | anchor: operational tooling, transaction validation, real-time workflows, internal product systems
- KPMG | India | September 2021 – July 2022 | bullets: 5 | anchor: audit and compliance systems, Java backend services, document processing, reporting workflows
- Trigent Software | India | March 2020 – August 2021 | bullets: 3 | anchor: frontend engineering, UI migration, responsive web delivery, QA-oriented implementation

Return only the final result matching the schema.
```

### What this removes from the live prompt

- long originality block
- repeated warnings about named tools
- repeated distributed-systems style warning
- longer project-story explanation
- repeated anti-overclaim language already covered elsewhere

### What we are relying on code to keep enforcing

- bullet count limits
- word count limits
- title sanitization
- malformed bullet detection
- generic phrase detection
- system context checks
- metric checks

### Main risk to watch

This version is faster and cleaner, but it may slightly increase:
- samey bullet structure
- less nuanced company differentiation

So after testing, the main review questions should be:
- are first bullets noticeably easier to scan?
- do later bullets still feel specific enough?
- do company sections still feel different from each other?

---

## Product-Level Direction

This is not a prompt rule, but a product rule we should keep in mind:

- faster generation matters because fast apply matters
- the system should optimize for fast usable drafts, not maximal per-call cleverness

That means:
- smaller prompts
- smaller payloads
- more code-side cleanup
- parallel generation where safe
