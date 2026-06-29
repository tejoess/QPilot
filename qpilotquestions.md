# QPilot — Multi-Agent Question Paper Generator

> A step-by-step breakdown of how the QPilot application works from start to finish.

---

## 1. The Orchestrator: LangGraph

The entire backend workflow is orchestrated by **LangGraph** (specifically using a `StateGraph` defined in `pipeline.py`).

**Role:** Think of LangGraph as the project manager. It doesn't write questions or analyze documents itself. Instead, it holds a central database of the progress (the `PipelineState`), passes data from one step to the next, and decides which specialized agent to call next.

**Workflows:** The orchestrator splits the generation process into three sequential, web-friendly workflows:

- **Analyze Syllabus Workflow** → `syllabus_fetch` → `syllabus_format`
- **Analyze PYQs Workflow** → `pyqs_fetch` → `pyqs_format`
- **Generate Paper Workflow** → `blueprint_build` → `blueprint_verify` → `question_select` → `paper_verify` → `final_generate`

---

## 2. The 6 Specialized Agents

As the Orchestrator runs, it calls 6 different **LLM-powered agents** (located in the `backend/services/` directory):

### Syllabus Formatting Agent
`backend/services/input_analysis/syllabus_service.py`

**Goal:** Takes raw syllabus text (extracted from uploaded PDFs or pasted text) and converts it into a clean, structured JSON format with module numbers, module names, weightages, and topics.

### PYQ (Previous Year Questions) Formatting Agent
`backend/services/input_analysis/pyq_service.py`

**Goal:** Reads past questions and maps/tags each question to a specific topic/subtopic in the structured syllabus.

### Blueprint Generator Agent
`backend/services/blueprint/blueprint_service.py`

**Goal:** Generates a question-by-question layout plan (a "blueprint") specifying the exact topic, mark allocation, and Bloom's taxonomy level (e.g., Remember, Understand, Apply) for every question slot without writing the actual question text yet.

### Blueprint Critic / Verifier Agent
`backend/services/blueprint/blueprint_verify.py`

**Goal:** Critiques the blueprint. It runs hard constraint checks in Python (e.g., Are the marks exactly equal to the target paper marks?) and uses an LLM to evaluate qualitative criteria (e.g., Is the difficulty progression natural? Does it match the teacher's focus areas?).

### Question Selector Agent
`backend/services/question_selection/question_service.py`

**Goal:** Fills the blueprint slots with actual questions by matching them with compatible questions from the PYQ pool.

### Question Paper Verifier Agent
`backend/services/question_verification/verify_paper.py`

**Goal:** Performs a final check on the completed drafted paper for quality, marks, and distribution constraints to decide if the paper is approved or needs revision.

---

## 3. Step-by-Step Flow: Input to Output

### Phase 1: Syllabus Parsing

**Input:** A Syllabus PDF or raw text.

- **Step 1 (`syllabus_fetch`):** Reads the PDF and extracts raw text. Saves it to `syllabus_raw.txt`.
- **Step 2 (`syllabus_format`):** The Syllabus Formatting Agent parses the raw text into `syllabus.json`.

### Phase 2: PYQ Analysis

**Input:** Past question papers (PDF or raw text) + the parsed `syllabus.json` from Phase 1.

- **Step 3 (`pyqs_fetch`):** Extracts raw text from the past papers. Saves it to `pyqs_raw.txt`.
- **Step 4 (`pyqs_format`):** The PYQ Formatting Agent organizes them into `pyqs.json`, mapping each past question to a syllabus topic.

### Phase 3: Paper Generation & Verification

**Input:** The structured syllabus, analyzed PYQs, teacher instructions (e.g., "Make it tough"), and desired Bloom's taxonomy distribution.

- **Step 5 (`blueprint_build`):** The Blueprint Generator Agent creates `blueprint.json` (the blueprint plan).
- **Step 6 (`blueprint_verify`):** The Blueprint Critic Agent evaluates the blueprint, saving feedback in `blueprint_verification.json`.
- **Step 7 (`question_select`):** The Question Selector Agent matches the blueprint slots with actual questions, creating `draft_paper.json`.
- **Step 8 (`paper_verify`):** The Question Paper Verifier Agent inspects the draft paper for a final rating and verdict.
- **Step 9 (`final_generate`):** Saves the finalized files (e.g., `final_paper.json`, summary metadata) to the server storage directory (`backend/services/data/{session_id}/`).

**Output:** A structured JSON object containing the verified question paper ready to be rendered in the React/Next.js frontend.

---

> `10:32 AM`

## Interview Q&A: Multi-Agent Coordination

**Q: How do things happen when 2 agents are speaking or coordinating to each other and a 3rd wants to coordinate with any of the agent which was previously talking to each other? How do we handle that — multithreaded or what else?**

This is a classic question about **Multi-Agent Coordination & Concurrency**.

When two agents (Agent A and Agent B) are interacting, and a third agent (Agent C) wants to interrupt or coordinate with one of them, handling it via traditional raw OS multithreading is usually avoided because LLMs are slow, state updates can cause race conditions, and debugging becomes a nightmare.

Instead, modern multi-agent frameworks (like LangGraph, AutoGen, or CrewAI) handle this using one of the following architectural patterns:

### 1. The Actor Model (Message-Based Concurrency) — *Recommended*

In frameworks like Microsoft AutoGen or Dapr, agents are modeled as **Actors**.

- **How it works:** Each agent has its own private state and a **Message Mailbox (Inbox)**.
- **The Scenario:** Agent A and Agent B are sending messages back and forth. Agent C wants to talk to Agent A.
- **How it's handled:** Agent C sends a message to Agent A's mailbox.
- **Concurrency Control:** Agent A processes messages from its inbox sequentially (one by one). While Agent A is "talking" to Agent B, Agent C's request sits in the queue. Once Agent A finishes its current turn, it picks up Agent C's message.
- **Why it's good:** It completely avoids race conditions and complex multithreading locks because each agent only does one thing at a time, even though the system as a whole is asynchronous.

### 2. Centralized State (Blackboard / Hub-and-Spoke Pattern)

This is how **LangGraph** (used in this repository) handles coordination.

- **How it works:** Agents do not talk to each other directly. Instead, they read from and write to a shared **Central State** (the "Blackboard").
- **The Scenario:** Agent A and Agent B write updates to the shared state. Agent C wants to join.
- **How it's handled:** The orchestrator (the Graph Router) manages the control flow. It pauses the interaction between A and B, reads the updated state, passes it to Agent C, and then routes the output back to Agent A.
- **Why it's good:** The state acts as a single source of truth. LangGraph handles this by using asynchronous step transitions rather than running them in parallel threads that crash into each other.

### 3. Async Event Loop (asyncio) instead of Multithreading

Since LLM calls are primarily network-bound (waiting for API responses), we don't need heavy CPU multithreading.

- **How it works:** We use Python's `async/await` event loop.
- **The Scenario:** Agent A, B, and C run as concurrent asynchronous tasks (`asyncio.gather` or background tasks).
- **How it's handled:** If Agent C needs to wait for Agent A to finish talking to Agent B, it uses an `asyncio.Event()` lock or a queue. Agent C awaits the event release. Once Agent A is free, it triggers the event, and Agent C resumes execution.

### Summary Checklist for an Interview

| Priority | Approach |
|----------|----------|
| **First Choice** | **Actor Model** — Message queues/mailboxes for each agent so they process inputs sequentially |
| **Second Choice** | **State Orchestrator / Blackboard** — A supervisor/router controls who talks when, updating a single shared state |
| **Execution Layer** | **Asynchronous Event Loops** (`asyncio`) or **Message Brokers** (Redis/Celery) — rather than raw CPU threads, because agents are waiting on network I/O (LLM APIs) rather than doing heavy CPU computations |

---

> `10:44 AM`

**Q: What have we used in this project?**

In this project (**QPilot**), we have used the **Centralized State (Blackboard Pattern) with Asynchronous Execution** via **LangGraph**.

Here is exactly how it is set up in your codebase:

### 1. Centralized State (`PipelineState`)

In `pipeline.py`, there is a single shared dictionary called `PipelineState`:

```python
class PipelineState(TypedDict):
    session_id: str
    syllabus: Optional[dict]
    pyqs: Optional[dict]
    blueprint: Optional[dict]
    draft_paper: Optional[dict]
    # ... other state variables
```

**How it coordinates:** Instead of the Blueprint Agent sending data directly to the Question Selector Agent, it simply writes its output (`blueprint`) to this shared `PipelineState`. When the next node starts, the orchestrator passes this updated state dictionary to it.

### 2. LangGraph Orchestration

The control flow is defined as a directed graph in `pipeline.py`:

```python
def build_graph():
    graph = StateGraph(PipelineState)
    # Define the agents/nodes
    graph.add_node("blueprint_build", blueprint_build_node)
    graph.add_node("blueprint_verify", blueprint_verify_node)
    # ...
    # Define the coordination path
    graph.add_edge("blueprint_build", "blueprint_verify")
    return graph.compile()
```

LangGraph acts as the **router/coordinator**. It ensures that the agents execute in a strict, predictable order without overlapping or causing concurrency issues.

### 3. Asynchronous Execution (`asyncio`)

Every step in the pipeline is defined using `async/await`:

```python
async def blueprint_verify_node(state: PipelineState):
    # awaits LLM response asynchronously
    blueprint_verdict = critique_blueprint(...) 
    return {"blueprint_verdict": blueprint_verdict}
```

Because these tasks are asynchronous, they run on Python's single-threaded event loop. If multiple users generate papers at the same time, the server handles them concurrently without needing complex OS multithreading locks.

---

> `10:46 AM`

## What is Asynchronous? (Explained in Simple Terms)

To understand **Asynchronous (Async)**, let's use a simple real-world analogy: **Cooking in a Kitchen**.

### 1. The Synchronous Way (Blocking)

Imagine you are boiling pasta and chopping vegetables:

1. You put the water on the stove.
2. You **stand there and stare at the pot**, doing absolutely nothing else until the water boils (takes 10 minutes).
3. Once it boils, you start chopping the vegetables.

**Synchronous means** you must finish one task completely before starting the next one. If a task takes time (like waiting for water to boil or waiting for an LLM to respond), the entire system freezes and waits.

### 2. The Asynchronous Way (Non-Blocking)

Now, imagine doing it the smart way:

1. You put the water on the stove.
2. Instead of waiting, you **set a timer and immediately start chopping vegetables**.
3. While the vegetables are cooking, you wash the dishes.
4. When the water boils, the stove "alerts" you, and you drop the pasta in.

**Asynchronous means** you don't wait around for slow tasks to finish. Instead, you start a task, hand it off, and work on other things in the meantime. When the slow task is done, it alerts you, and you handle the result.

### Why do we use Async in QPilot?

When QPilot calls Gemini or OpenAI to generate a question paper, the LLM might take **10 to 30 seconds** to respond.

- **If QPilot were synchronous:** The entire backend server would freeze for those 30 seconds. No other user could load the website or click buttons.
- **Because QPilot is asynchronous:** The server sends the request to the LLM and immediately says, *"I'm going to handle other tasks (like sending progress logs to the frontend via WebSockets) while I wait for the LLM to get back to me."*

---

> `10:50 AM`

## What are `async` and `await`? (Cooking Analogy)

Think of `async` and `await` as **special instructions written on a recipe card** for a chef:

### 1. `async` (Making the recipe multi-task friendly)
When you prefix a function with `async`, you tell the chef:
> *"This recipe contains steps where you will have to wait around. Do not stand still; be prepared to switch to other recipes/tasks while waiting."*

* **In code:** `async def generate_paper()` means this function is allowed to pause and let the server handle other things while it waits.

### 2. `await` (Setting a timer and stepping away)
When you put `await` in front of a slow action, you tell the chef:
> *"Start this task, set a timer, and immediately walk away to work on other things. Do not move to the next step of this specific recipe until the timer goes off."*

* **In cooking:**
  ```text
  Step 1: Mix cake batter.
  Step 2: AWAIT Bake in oven (30 minutes).
  Step 3: Put icing on the cake.
  ```
  While the cake is in the oven (`await`ing), the chef washes dishes or chops veggies for other orders. But the chef **cannot** proceed to Step 3 (icing the cake) until the baking timer finishes.

* **In code:**
  ```python
  raw_text = await syllabus_fetch()  # Step away while PDF reads
  formatted_json = await syllabus_format(raw_text)  # Run only after raw_text is ready
  ```

---

> `10:57 AM`

## 6 Key Concepts Every AI/Agent Engineer Must Know

Here are 6 essential concepts and patterns you need to master for AI engineering interviews and real-world development:

### 1. Structured Outputs & JSON Mode
* **What it is:** Ensuring an LLM outputs structured, valid JSON (matching a specific schema/Pydantic model) instead of plain conversational text.
* **Why it matters:** If an LLM returns a conversational prefix like *"Here is your JSON:"* or misshapes a key, your code's parser will crash.
* **How it's handled:** Using features like **Instructor**, **OpenAI Structured Outputs**, or Pydantic validation to enforce schemas. In this repository, we use regex fallback parsers and automated JSON repair functions (`fix_incomplete_json`) to make the parsing resilient.

### 2. Retrieval-Augmented Generation (RAG) vs. Fine-Tuning
* **What it is:** Two ways to customize an LLM with private data. 
  * **RAG:** Searching a database/files for relevant context and pasting it directly into the prompt (like giving the LLM an open-book exam).
  * **Fine-Tuning:** Retraining the model's actual weights on a custom dataset (like studying and memorizing material before an exam).
* **When to use what:** 
  * Use **RAG** for dynamic data, factual accuracy, and referencing documents (like syllabus files).
  * Use **Fine-Tuning** for teaching a specific tone, formatting style, or domain-specific language structure.

### 3. Prompt Reasoning Patterns (CoT, Few-Shot, ReAct)
* **What they are:** Techniques to improve LLM problem-solving accuracy.
  * **Few-Shot Prompting:** Giving 2-3 examples of inputs and desired outputs inside the prompt so the LLM understands the exact pattern.
  * **Chain-of-Thought (CoT):** Asking the LLM to *"think step-by-step"* to reason through complex logic before returning the final answer.
  * **ReAct (Reasoning + Acting):** Letting the LLM loop through a cycle: Think $\rightarrow$ Call a Tool $\rightarrow$ Read Tool Output $\rightarrow$ Repeat until solved.

### 4. Agent Memory (Short-Term vs. Long-Term)
* **What it is:** How agents recall previous interactions.
  * **Short-Term Memory:** Keeping track of the current conversation history (usually by passing the list of recent messages back to the LLM on every turn).
  * **Long-Term Memory:** Storing user preferences, historical sessions, or external facts in a database (like a vector database or database storage) to retrieve them days or weeks later.

### 5. AI Evaluations ("Evals") and Guardrails
* **What it is:** How you measure if your agent is doing a good job and keep it safe.
  * **Evals:** Running programmatic tests (like a unit test suite for LLMs) using packages like `Ragas` to score LLM outputs on faithfulness, relevance, and accuracy.
  * **Guardrails:** Intercepting inputs and outputs (using tools like `Guardrails AI` or system prompts) to prevent prompt injections, toxic content, and hallucinations.

### 6. System Latency & Cost Optimization
* **What it is:** Balancing speed, cost, and intelligence.
* **How to solve it:**
  * **Semantic Routing:** Directing easy questions (e.g. *"Hello!"*) to a fast, cheap model (like Gemini Flash / GPT-4o-mini) and hard tasks (complex blueprint generation) to smart models (like Gemini Pro / GPT-4o).
  * **Prompt Caching:** Reusing prompt prefixes (like large syllabus texts) to reduce token processing costs and speed up response times.

