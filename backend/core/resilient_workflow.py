"""
Resilient Workflow Engine - Self-healing wrapper around standard workflow
with automatic retry, validation, and graceful degradation.
"""

import logging
import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime
from backend.core.event_bus import get_event_bus, WorkflowEvent, EventType, EventSeverity
from backend.core.config import Config

logger = logging.getLogger(__name__)


class ResilientWorkflowEngine:
    """
    Self-healing workflow engine that wraps stage execution with:
    - Automatic retry with exponential backoff
    - Output validation
    - Graceful degradation
    - Human escalation when retries exhausted
    """
    
    def __init__(self, project_id: str, max_retries: int = None):
        """
        Initialize resilient workflow engine
        
        Args:
            project_id: Project identifier
            max_retries: Maximum retry attempts (defaults to Config.MAX_RETRIES)
        """
        self.project_id = project_id
        self.max_retries = max_retries or Config.MAX_RETRIES
        self.event_bus = get_event_bus()
        self.retry_counts = {}  # stage_name -> retry_count
        
        logger.info(f"ResilientWorkflowEngine initialized for project {project_id}")
    
    async def execute_stage_with_retry(
        self,
        stage_name: str,
        execute_fn: Callable,
        validate_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute a stage with automatic retry and validation
        
        Args:
            stage_name: Name of the stage
            execute_fn: Async function that executes the stage
            validate_fn: Optional validation function for output
        
        Returns:
            Stage execution result
        
        Raises:
            Exception: If all retries exhausted and validation fails
        """
        self.retry_counts[stage_name] = 0
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Executing {stage_name} (attempt {attempt + 1}/{self.max_retries})")
                
                # Execute stage
                result = await execute_fn()
                
                # Validate output if validator provided
                if validate_fn:
                    is_valid, validation_msg = await self._validate_output(
                        stage_name,
                        result,
                        validate_fn
                    )
                    
                    if not is_valid:
                        raise ValueError(f"Validation failed: {validation_msg}")
                
                # Success!
                logger.info(f"{stage_name} completed successfully")
                return result
            
            except Exception as e:
                last_error = e
                self.retry_counts[stage_name] = attempt + 1
                
                logger.error(f"{stage_name} failed (attempt {attempt + 1}): {e}")
                
                # Emit retry event
                await self._emit_retry_event(stage_name, attempt + 1, str(e))
                
                # If not last attempt, wait with exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = Config.RETRY_DELAY_SECONDS * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    # All retries exhausted
                    await self._emit_escalation_event(stage_name, str(last_error))
        
        # If we get here, all retries failed
        raise RuntimeError(
            f"Stage {stage_name} failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )
    
    async def execute_with_fallback(
        self,
        stage_name: str,
        primary_fn: Callable,
        fallback_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute with fallback strategy
        
        Args:
            stage_name: Stage name
            primary_fn: Primary execution function
            fallback_fn: Fallback function if primary fails
        
        Returns:
            Execution result
        """
        try:
            return await self.execute_stage_with_retry(stage_name, primary_fn)
        
        except Exception as e:
            if fallback_fn:
                logger.warning(f"{stage_name} primary failed, trying fallback")
                
                await self.event_bus.emit(WorkflowEvent(
                    event_type=EventType.WARNING_ISSUED,
                    timestamp=datetime.now().isoformat(),
                    project_id=self.project_id,
                    stage=stage_name,
                    message=f"Primary execution failed, using fallback strategy",
                    data={"primary_error": str(e)},
                    severity=EventSeverity.WARNING
                ))
                
                return await fallback_fn()
            else:
                raise
    
    async def _validate_output(
        self,
        stage_name: str,
        output: Dict[str, Any],
        validate_fn: Callable
    ) -> tuple[bool, str]:
        """
        Validate stage output
        
        Returns:
            (is_valid, message)
        """
        try:
            if asyncio.iscoroutinefunction(validate_fn):
                is_valid = await validate_fn(output)
            else:
                is_valid = validate_fn(output)
            
            if is_valid:
                return True, "Validation passed"
            else:
                return False, "Validation failed - output does not meet requirements"
        
        except Exception as e:
            logger.error(f"Validation function failed: {e}")
            return False, f"Validation error: {str(e)}"
    
    async def _emit_retry_event(self, stage_name: str, attempt: int, error: str):
        """Emit retry attempt event"""
        await self.event_bus.emit(WorkflowEvent(
            event_type=EventType.RETRY_ATTEMPT,
            timestamp=datetime.now().isoformat(),
            project_id=self.project_id,
            stage=stage_name,
            message=f"Retry attempt {attempt}/{self.max_retries} for {stage_name}",
            data={
                "attempt": attempt,
                "max_retries": self.max_retries,
                "error": error
            },
            severity=EventSeverity.WARNING
        ))
    
    async def _emit_escalation_event(self, stage_name: str, error: str):
        """Emit human escalation event"""
        await self.event_bus.emit(WorkflowEvent(
            event_type=EventType.HUMAN_INPUT_REQUIRED,
            timestamp=datetime.now().isoformat(),
            project_id=self.project_id,
            stage=stage_name,
            message=f"Stage {stage_name} requires human intervention after failed retries",
            data={
                "error": error,
                "retries_attempted": self.max_retries,
                "escalation_reason": "All automatic retry attempts exhausted"
            },
            severity=EventSeverity.CRITICAL
        ))
    
    def get_retry_stats(self) -> Dict[str, int]:
        """Get retry statistics for all stages"""
        return self.retry_counts.copy()


# Helper validators
def validate_has_success_field(output: Dict[str, Any]) -> bool:
    """Validate output has success field"""
    return output.get("success", False) == True


def validate_has_required_keys(required_keys: List[str]) -> Callable:
    """Create validator that checks for required keys"""
    def validator(output: Dict[str, Any]) -> bool:
        return all(key in output for key in required_keys)
    return validator


def validate_no_errors(output: Dict[str, Any]) -> bool:
    """Validate output has no error field"""
    return "error" not in output or output["error"] is None
