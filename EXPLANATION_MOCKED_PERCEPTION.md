# What is "Mocked Perception"?

In the current Stage 4 demo, the **Visual Cortex** has two jobs:
1.  **Extract Logic:** Read "rm -rf" and understand it as a command. (This is **REAL**).
2.  **Generate Vectors:** Creating a list of numbers (e.g., `[0.12, -0.98...]`) that represents the "concept" of the text for similarity search.

**The Mock:**
Instead of paying OpenAI to generate these numbers (which requires an API key and internet), I used a mathematical trick to generate "stable random numbers" from the text.
*   **Real:** `OpenAI.embed("Hello")` -> `[0.8, -0.1...]` (Meaningful)
*   **Mock:** `Random(Seed="Hello")` -> `[0.5, 0.2...]` (Meaningless but consistent)

**Why?**
This allows the system to run **offline** and **fast** for testing the *Thinking Loop*. The *Thinking* (Reptile Brain) relies on the Logic (Real), not the Vectors (Mock), so the demo's behavior (Planning, Vetoing) is 100% valid.
