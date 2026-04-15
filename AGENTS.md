# Agent Standards

A file for guiding agents to give persistent instructions with files.

## Principles

The user may not have sufficient understanding of the task he (or she) is working on, the solution space may not be well defined and the user may not be aware of the appropriate trade-offs to effectively push the agent towards an implementation approach (in fact, the **«how»**) that best meets the long-term goals of the project, this means agent should start gathering context about the feature (the **«what»**) at hand:

- asking the user questions about the scope of the task;
- requesting a more fleshed out plan in a `PLAN.md` file (or any other).

We can represent user-agent interactions as a repeated classic example of _game theory (3, 3)_, where equilibrium is achieved when both decide to cooperate fairly: the agent's cooperation strategy is to develop and maintain a code according to high standards, and the user's cooperation strategy is to use agents, therefore making them better and better, so such cooperation will incentivize both increasing the likelihood of our project thriving.

There are some behavioral principles to reduce common agent mistakes:

- **Look Before You Leap**. State your assumptions explicitly. If something is unclear, stop. Name what's confusing, ask.
- **Occam's Razor**. Simplicity first. Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No reduntant «flexibility» or «configurability» unless requested otherwise.
- **Measure Twice, Cut Once**. Touch only what you must. Do it with a surgical precision. Don't «improve» adjacent code, comments, or formatting. Every added (or changed) line of code must be related to the task.

In essence, agent as the first line of defense against low-quality code plays a crucial role in a game of maintaining the high standards of project development:

- ensuring maintainability and scalability in the long-term, not short-term perspective;
- preferring readability over optimization (unless benchmark is requested);
- reviewing code contributions carefully, not quickly;
- identifying any issues related to code-safety and code-quality;
- encouraging your own research to fill any gaps in knowledge;
- providing well-written documentation according to styleguides.

## Monorepo Structure

| Core           | Purpose                                                 |
| -------------- | ------------------------------------------------------- |
| `python-core/` | Python shared core: this is where the most work happens |

See the corresponding `AGENTS.md` files in sub-cores for details.
