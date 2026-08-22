# Build Your First AI-Native Power Electronics Tool

**For power-electronics engineers who know converters—but not Python.**

The promise is not that AI will approve a converter. The promise is that an
engineer can translate rules, simulations and measurements into auditable
automation while retaining engineering authority.

| Field Note | Reader outcome | Executable artifact |
|---|---|---|
| 1. Before You Ask AI to Build an LLC Tool, Define What Pass Means | Distinguish electrical reject, method failure and human approval | Decision contract + up to three cases |
| 2. Can Another Engineer Rebuild the Workflow from a Clean Machine? | Change a specification and rebuild the workflow | Notebook + quick demo + clean-copy test |
| 3. When Does a Simulation Result Become a Training Label? | Export targets without contaminating failures | Dataset schema + dictionaries + dataset card |
| 4. Train Your First LLC Surrogate Without Hiding Bad Data | Compare a simple regressor with baselines | Training notebook |
| 5. The Accuracy Trap: Test Designs the Model Has Never Seen | Prevent design leakage and inspect residuals | Split manifest + evaluation template |
| 6. Build a Tool That Knows When Not to Answer | Add domain limits, abstention and review | Simple interface + abstention rule |

The current package combines the executable artifacts needed to support Field
Notes 1 and 2 and prepares—but does not claim completion of—the dataset contract
for Field Note 3.

## Repeated format

Each delivery should contain:

1. one engineering decision;
2. the brief given to the coding assistant;
3. what the assistant implemented;
4. what the engineer had to decide or correct;
5. one result;
6. one real or explicitly synthetic failure;
7. one executable artifact;
8. a 10–20 minute exercise;
9. the boundary resolved by the next delivery.
