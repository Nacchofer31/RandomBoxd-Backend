"""LangGraph workflow definition - orchestrates the recommendation pipeline."""

from langgraph.graph import END, StateGraph

from app.workflow.nodes.extract_preferences import extract_preferences
from app.workflow.nodes.final_recommendation import final_recommendation
from app.workflow.nodes.score_movies import score_movies
from app.workflow.nodes.validate_pool import validate_pool
from app.workflow.state import WorkflowState


def should_continue(state: WorkflowState) -> str:
    """
    Determine whether to continue the workflow or stop due to an error.

    Returns:
        "continue" if no error, "error" if there's an error
    """
    if state.error:
        return "error"
    return "continue"


def build_recommendation_workflow() -> StateGraph:
    """
    Build the LangGraph workflow for movie recommendation.

    Flow:
    START -> validate_pool -> (error?) -> extract_preferences
    -> score_movies -> final_recommendation -> END
    (-> END if error after validate_pool)
                                     -> END (if error)
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("validate_pool", validate_pool)
    workflow.add_node("extract_preferences", extract_preferences)
    workflow.add_node("score_movies", score_movies)
    workflow.add_node("final_recommendation", final_recommendation)

    # Define edges with conditional routing
    workflow.set_entry_point("validate_pool")

    # After validate_pool, check for errors
    workflow.add_conditional_edges(
        "validate_pool",
        should_continue,
        {
            "continue": "extract_preferences",
            "error": END,
        },
    )

    workflow.add_edge("extract_preferences", "score_movies")
    workflow.add_edge("score_movies", "final_recommendation")
    workflow.add_edge("final_recommendation", END)

    return workflow.compile()


# Global workflow instance
recommendation_workflow = build_recommendation_workflow()
