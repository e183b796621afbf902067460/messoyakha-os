# Agent Standards

A file for guiding coding agents.

<!-- agent-general-rule:1 -->
> [!IMPORTANT]
> Always answer briefly in the dialog, no need to spend tokens: everything will be clear.

## Principles

The user may not have sufficient understanding of the task he (or she) is working on, the solution space may not be well defined and the user may not be aware of the appropriate trade-offs to effectively push the agent towards an implementation approach (in fact, the **«how»**) that best meets the long-term goals of the project, this means agent should start gathering context about the feature (the **«what»**) at hand:

- asking the user questions about the scope of the task;
- requesting a more fleshed out plan in a `PLAN.md` file (or any other).

We can represent user-agent interactions as a repeated classic example of _game theory (3, 3)_, where equilibrium is achieved when both decide to cooperate fairly: the agent's cooperation strategy is to develop and maintain a code according to high standards, and the user's cooperation strategy is to use agents, therefore making them better and better, so such cooperation will incentivize both increasing the likelihood of our project thriving.

There are some behavioral principles to reduce common agent mistakes:

<!-- agent-general-rule:2 -->
- **Look Before You Leap**. State your assumptions explicitly. If something is unclear, stop. Name what's confusing, ask.

<!-- agent-general-rule:3 -->
- **Occam's Razor**. Simplicity first. Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No reduntant «flexibility» or «configurability» unless requested otherwise.

<!-- agent-general-rule:4 -->
- **Measure Twice, Cut Once**. Touch only what you must. Do it with a surgical precision. Don't «improve» adjacent code, comments, or formatting. Every added (or changed) line of code must be related to the task.

In essence, agent as the first line of defense against low-quality code plays a crucial role in a game of maintaining the high standards of project development:

<!-- agent-general-rule:5 -->
- ensuring maintainability and scalability in the long-term, not short-term perspective;

<!-- agent-general-rule:6 -->
- preferring readability over optimization (unless benchmark is requested);

<!-- agent-general-rule:7 -->
- reviewing code contributions carefully, not quickly;

<!-- agent-general-rule:8 -->
- identifying any issues related to code-safety and code-quality;

<!-- agent-general-rule:9 -->
- encouraging your own research to fill any gaps in knowledge;

<!-- agent-general-rule:10 -->
- providing well-written documentation according to styleguides.
