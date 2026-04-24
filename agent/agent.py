"""
LangChain Agent – The core agentic AI that orchestrates the entire job application pipeline.
Uses OpenAI function calling with custom tools to make intelligent decisions about
which jobs to apply to and how to customize responses.
"""

import logging
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

from config import Config
from .tools import get_all_tools

logger = logging.getLogger(__name__)

# System prompt that defines the agent's personality and decision-making framework
AGENT_SYSTEM_PROMPT = """You are an AI Job Application Agent — a smart career assistant that helps 
job seekers find, evaluate, and apply to the best opportunities.

## Your Capabilities
You have access to tools that allow you to:
1. **Scrape job listings** from LinkedIn and Internshala
2. **Read the user's resume** to understand their skills and experience
3. **Match jobs** against the resume and score them
4. **Make decisions** about which jobs are worth applying to
5. **Generate tailored cover letters** for recommended positions
6. **Track applications** and their statuses

## Decision-Making Framework
When evaluating jobs, consider these factors and score each 0-1:

1. **Skills Match (40%)**: How many of the required skills does the candidate have?
2. **Experience Alignment (25%)**: Does the candidate's experience level match?
3. **Role Relevance (20%)**: How relevant is the job title to the candidate's career goals?
4. **Growth Potential (15%)**: Does this role offer learning and career growth?

**Decision thresholds:**
- Score ≥ 0.7 → **APPLY** (strong match, generate cover letter)
- Score 0.4-0.7 → **REVIEW** (moderate match, flag for user review)
- Score < 0.4 → **SKIP** (poor match, save but don't pursue)

## Guidelines
- Always read the resume before evaluating any jobs
- Be thorough in your analysis but concise in explanations
- When generating cover letters, make them genuinely personalized — don't use generic templates
- Provide honest assessments; don't inflate match scores
- Track everything so the user can review your decisions
- When the user asks about progress, use the stats tool to give accurate numbers

## Communication Style
- Be professional yet friendly
- Use bullet points for clarity
- Provide specific evidence for your match assessments
- Always explain your reasoning for apply/skip decisions
"""


class JobApplicationAgent:
    """
    The main agentic AI that orchestrates the job application pipeline.
    Uses LangChain's OpenAI tools agent with custom tools and memory.
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY,
        )
        self.tools = get_all_tools()
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=20  # Keep last 20 exchanges
        )
        self.agent_executor = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with tools and memory."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", AGENT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=15,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )

    def run(self, user_input: str) -> dict:
        """
        Process a user request through the agent.

        Args:
            user_input: Natural language instruction from the user

        Returns:
            dict with 'output' (the response) and 'steps' (intermediate actions)
        """
        try:
            result = self.agent_executor.invoke({"input": user_input})

            # Extract intermediate steps for transparency
            steps = []
            for step in result.get("intermediate_steps", []):
                action, observation = step
                steps.append({
                    "tool": action.tool,
                    "input": str(action.tool_input)[:500],
                    "output": str(observation)[:500],
                })

            return {
                "output": result["output"],
                "steps": steps,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "output": f"I encountered an error: {str(e)}. Please check your API key and try again.",
                "steps": [],
                "success": False,
            }

    def quick_match(self, user_input: str = None) -> dict:
        """
        Run the full matching pipeline: read resume → get unmatched jobs → evaluate → decide.
        This is a convenience method for batch processing.
        """
        prompt = user_input or (
            "Please do the following:\n"
            "1. Read my resume\n"
            "2. Get all unmatched/unprocessed jobs\n"
            "3. Evaluate each job against my resume\n"
            "4. Save match results with scores and decisions\n"
            "5. Generate cover letters for jobs you recommend applying to (score >= 0.7)\n"
            "6. Give me a summary of results"
        )
        return self.run(prompt)

    def scrape_and_match(self, query: str, sources: list[str] = None,
                         location: str = "India") -> dict:
        """
        Full pipeline: scrape new jobs → match → generate cover letters.
        """
        sources = sources or ["linkedin", "internshala"]
        source_list = ", ".join(sources)

        prompt = (
            f"Please do the following:\n"
            f"1. Scrape job listings for '{query}' in '{location}' from: {source_list}\n"
            f"2. Read my resume\n"
            f"3. Evaluate ALL the newly scraped jobs against my resume\n"
            f"4. For each job, save the match result with a score and decision\n"
            f"5. Generate cover letters for any jobs scoring 0.7 or above\n"
            f"6. Give me a detailed summary including:\n"
            f"   - How many jobs were found\n"
            f"   - How many are recommended (score >= 0.7)\n"
            f"   - Top 5 matches with details\n"
            f"   - Any cover letters generated"
        )
        return self.run(prompt)
