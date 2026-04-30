# Resume Prompt Refinement Notes

## Goal

Build a tailored resume for any JD that:

- feels believable and production-level
- is optimized for recruiter scanability and ATS compatibility
- emphasizes fit, not full career history
- preserves originality and natural tone
- avoids generic, robotic, or obviously AI-shaped writing

This document captures:

1. What we learned from the articles and prompt examples
2. What we observed in the app outputs
3. What prompt/system changes we should make next


## Core Principle

The resume is not a full professional biography.

It is a targeted sales document whose job is to:

- survive the recruiter’s first scan
- make the candidate look like a strong fit
- earn the recruiter phone call

That means:

- highlight relevant evidence
- compress less relevant evidence
- keep top sections strong and easy to scan
- make recent, relevant experience do most of the selling


## What We Learned From the Articles

### 1. The resume must optimize for the first scan

Recruiters and hiring managers typically:

1. scan in a few seconds
2. only then do a second read if the first scan matches the role

So the generated resume should make these obvious immediately:

- target role
- years of experience
- strongest systems/capabilities
- key technologies
- recent relevant experience

Implication for prompt:

- write for first-scan clarity, not just completeness


### 2. Relevance matters more than completeness

The candidate does not need every role and every detail presented evenly.

More relevant and recent work should carry more weight.
Older or less relevant work should be shorter and more supportive.

Implication for prompt:

- emphasize relevant experience
- compress less relevant experience
- do not tell the whole story evenly


### 3. Summary matters more for experienced candidates

For experienced candidates, the summary often matters more because it frames:

- who this person is
- what kind of systems they build
- why they match the role

Implication for prompt:

- summary must be a fit statement, not a generic intro


### 4. Skills section should answer one recruiter question quickly

Recruiters want to answer:

> What languages and technologies is this person hands-on with?

The section should be:

- easy to scan
- relevant to the role
- not bloated
- not a list of everything ever touched

Implication for prompt:

- skills should include relevant hands-on capabilities only
- no expertise labels
- no trivial apps/editors/tools
- strongest and most relevant items first


### 5. Work experience should reinforce technologies

The skills section should provide scanability.
The experience section should prove actual use.

Implication for prompt:

- important skills/technologies should also appear naturally in bullets
- recent usage should be visible through experience


### 6. Achievement bullets need structure

Useful bullet-writing pattern from the articles:

Action Verb + System/Noun + Tool/Method + Constraint/Decision + Metric/Outcome

Implication for prompt:

- bullets should describe accomplishments, not responsibilities
- every bullet should show impact, not just work performed


### 7. Specificity, numbers, and active language matter

Strong resumes stand out by being concrete.

The articles reinforce that bullets should:

- quantify impact whenever possible
- use active language, not passive “worked on” phrasing
- mention relevant technologies where they add useful context
- explain what changed because of the work

Implication for prompt:

- prefer concrete numbers, scale signals, and operational outcomes
- prefer active verbs and proactive framing
- avoid vague responsibility-style language


### 8. Tailoring means changing emphasis, not rewriting history

Tailoring is not only about swapping words.

It can also mean:

- moving more relevant signals higher
- giving more space to relevant recent work
- compressing less relevant or older work
- choosing the most role-relevant details first

Implication for prompt:

- shape emphasis and detail density by role relevance
- let recent, relevant sections carry more of the story


### 9. Humanization matters

AI writing becomes obvious when it is:

- too polished
- too repetitive
- too dramatic
- too formulaic

Useful humanization guidance:

- use nondramatic language
- vary sentence openings and structures
- avoid inflated marketing tone
- replace generic phrases with specific engineering language

Implication for prompt:

- add a final tone pass for natural, human-sounding writing


### 10. ATS optimization matters, but not as keyword stuffing

ATS-friendly content should:

- align naturally with the JD
- include relevant qualifications and terminology
- preserve readability for human reviewers

We should not optimize for fake “80% ATS score” guarantees.
The article also reinforces that, in tech, resumes are still read by humans and should be written for recruiter and hiring-manager review first.
ATS systems mainly help recruiters track application status through the hiring pipeline; they are not acting as magical autonomous resume judges.

Implication for prompt:

- use ATS-aware phrasing naturally
- do not stuff keywords
- do not treat ATS as the primary audience over human reviewers


### 11. ATS myths should not drive prompt design

The ATS articles reinforce a few practical truths:

- recruiters and hiring managers still review resumes directly
- major ATS tools are workflow systems, not automated rejection engines
- “beat the ATS” advice is often exaggerated or commercially motivated
- PDF format is not the real issue in tech hiring; relevance and readability are

Implication for prompt:

- optimize for human review speed and clarity first
- treat ATS compatibility as clean structure and natural terminology coverage
- do not over-design the resume around imaginary parser tricks


## What We Learned From Testing Current Outputs

### Strengths

- summaries have improved in role alignment
- bullets are more structured than before
- Trigent is no longer drifting into obvious AI content
- the two-call analysis + generation architecture is the right direction


### Recurring Problems

#### 1. Experience formatting bug

Observed output:

```text
McKinsey & Company | CA, USA
McKinsey & Company | CA, USA | May 2025 – Present | May 2025 – Present
```

Meaning:

- model sometimes writes metadata into the title field
- output formatting breaks the role line

Status:

- formatter-side cleanup added
- prompt also updated to say role title field must contain title only


#### 2. Skills section quality is unstable

Observed issues:

- categories collapse together
- skills feel like keyword matching
- supporting skills are weak or missing
- too much stack dumping

Meaning:

- prompt needs stronger skill derivation rules
- skills need to feel system-capable, not taxonomy-shaped


#### 3. Over-invented stack precision

Observed repeated examples:

- Envoy
- Helm
- Terraform
- Kafka Streams
- Loki
- Elasticsearch
- Storybook
- Cypress

Meaning:

- prompt still allows the model to satisfy “role fit” by inventing impressive stack details
- the model overfits to the target JD’s architecture style


#### 4. Bullets sound synthetic

Observed issues:

- bullets often read like “benchmark distributed systems engineer” outputs
- too polished
- too dramatic
- too stack-heavy
- not grounded enough in believable transferable work


#### 5. Company sections do not always feel like one project story

Observed issues:

- bullets are individually strong
- but some company sections feel like unrelated impressive bullets

Meaning:

- sequencing rule needs to be more operational


## Current Understanding of What the Prompt Must Do

The prompt must do all of the following:

### A. Understand the soul of the JD

It should identify:

- the real problem
- the target system
- the workflow
- the success model
- must-have capabilities
- supporting system capabilities
- signals to emphasize
- gaps not to invent


### B. Build a recruiter-optimized resume

It should produce:

- a strong title
- a role-aligned summary
- a scanable skills section
- believable work history bullets


### C. Keep the content believable

It should:

- use transferable systems, not forced exact stack substitution
- prefer analogous systems over invented expertise
- maintain realistic technology progression over time


### D. Keep the tone natural

It should:

- use nondramatic language
- sound human
- preserve action/result orientation
- avoid stiff AI polish


## Prompt Problems Still Remaining

### 1. Role alignment still overpowers grounding

Current prompt still rewards:

- looking like the target role

more than:

- sounding like the candidate’s real explainable background


### 2. Supporting skill derivation is still not precise enough

The prompt says to include supporting skills, but:

- it does not yet tightly control what a “complete system-capable toolkit” looks like
- it still allows underpowered or overstuffed skills sections


### 3. Originality is requested but not fully operationalized

The prompt says:

- preserve originality
- avoid generic phrasing

But the model still finds synthetic “strong backend engineer” language patterns.


### 4. Company story rule is still too abstract

It says:

- early bullets = system/problem
- middle bullets = implementation
- later bullets = impact/reliability

But the model still sometimes produces six strong disconnected bullets.


### 5. ATS and natural tone still pull against each other

The prompt asks for:

- ATS alignment
- natural human tone

The model still sometimes satisfies ATS by becoming too stiff or too polished.


## Prompt Changes We Thought Of Making

These are the prompt changes we should make next after using this document as the source of truth.

### 1. Stronger recruiter-scan rule

Add:

- the resume is a targeted fit document, not a full career history
- optimize for first-scan clarity
- make top sections do most of the selling


### 2. Stronger summary rule

Summary should:

- be 65–95 words
- quickly explain fit
- show strongest systems built
- show role-relevant problems solved
- sound specific and nondramatic
- feel like “this person already does this job”


### 3. Stronger skills rule

Skills section should:

- answer “what is this person hands-on with?”
- include both:
  - core JD-facing skills
  - supporting production system skills
- be scanable
- avoid expertise labels
- avoid trivial tools
- avoid giant stack dumps
- include only relevant hands-on technologies

Also:

- important technologies in the skills section should appear in work history where relevant


### 4. Stronger bullet-writing rule

Use this formula explicitly:

Action Verb + System/Noun + Tool/Method + Constraint/Decision + Metric/Outcome

Each bullet should:

- describe an achievement
- not read like a responsibility
- include system context
- include 1–3 relevant tools/skills
- include a real constraint or technical decision
- include a measurable result


### 5. Stronger anti-generic rule

Each bullet should internally pass:

> Can this apply to 1000 engineers?

If yes:

- rewrite with:
  - more specific system
  - real constraint
  - real technical decision


### 6. Stronger project-story rule

Each company should read as one coherent body of work:

- bullet 1–2: establish system and problem
- bullet 3–4: implementation and design decisions
- bullet 5–6: reliability, validation, scale, impact

Company sections should not feel like random strong bullets.


### 7. Stronger originality rule

Add:

- preserve originality
- map JD needs through believable transferable systems
- prefer analogous systems over perfect stack matching
- vary verbs, sentence openings, technical decisions, and metric shapes


### 8. Stronger humanization rule

Add:

- use nondramatic language
- avoid stiff, repetitive, over-polished phrasing
- vary sentence structure
- sound like a strong real engineer, not AI-polished marketing copy


### 9. Stronger ATS rule

Add:

- align language naturally to the JD
- include relevant qualifications and terminology credibly
- optimize for ATS without keyword stuffing
- keep human readability as a hard requirement
- write for recruiter and hiring-manager scan first, not for imaginary robot rejection
- treat ATS as a workflow environment, not the primary decision-maker


### 10. Stronger timeline realism rule

Add:

- only use technologies that fit the time period and believable exposure progression
- favor realistic evolution of experience over dramatic stack jumps


## What We Should Not Do

- do not turn the app into a job-fit rejection engine
- do not optimize for a fake universal ATS score
- do not treat ATS as the primary audience over the recruiter or hiring manager
- do not design prompts around “beating bots” myths
- do not let the prompt become a giant bloated instruction dump again
- do not solve all grounding problems only with more adjectives in the prompt


## Recommended Final Prompt Architecture

### Prompt 1: JD Analysis

Purpose:

- extract full JD intelligence
- find the soul of the role
- separate core vs supporting skills
- surface gaps and build strategy


### Prompt 2: Resume Generation

Purpose:

- generate title, summary, skills, and experience
- use the analysis as source of truth
- enforce structure, recruiter scanability, ATS-aware language, believable systems, and natural tone


## Implementation Plan

### Immediate

1. keep this document as the working reference
2. use it to revise the prompts
3. test on the same JD repeatedly

### After prompt revisions

Check:

- title quality
- summary quality
- skills section scanability
- supporting skill presence
- bullet originality
- project-story quality
- formatting stability


## Final Note

The main challenge is no longer “add more rules.”

The challenge is:

- keep the prompt sharp
- keep it grounded
- keep it readable
- keep it natural
- keep it recruiter-effective

This document should be the source of truth before further prompt changes.
