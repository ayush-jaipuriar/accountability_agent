"""
Daily Tasks Service
===================

Handles Firestore CRUD operations and business logic for the Daily Focus Engine (To-Dos).
Path: daily_tasks/{user_id}/tasks/{date}
"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple

from src.models.schemas import DailyTaskList, DailyTaskItem
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class TaskService:
    """Manage daily focus lists in Firestore."""

    def __init__(self):
        self.firestore = firestore_service

    def get_daily_tasks(self, user_id: str, date: str) -> Optional[DailyTaskList]:
        """
        Fetch daily task list for a user on a specific date.
        
        Args:
            user_id: User ID
            date: Date string (YYYY-MM-DD)
            
        Returns:
            DailyTaskList or None
        """
        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc = doc_ref.get()
            if doc.exists:
                return DailyTaskList.from_firestore(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error fetching daily tasks: {e}", exc_info=True)
            return None

    def create_or_get_daily_tasks(
        self, user_id: str, date: str, primary_title: str
    ) -> DailyTaskList:
        """
        Get daily task list or initialize it with a primary task.
        
        Args:
            user_id: User ID
            date: Date string (YYYY-MM-DD)
            primary_title: Title of the primary task (stated priority)
            
        Returns:
            DailyTaskList
        """
        existing = self.get_daily_tasks(user_id, date)
        if existing:
            return existing

        # Ensure primary title has fallback
        if not primary_title or not primary_title.strip():
            primary_title = "Maintain consistency"

        # Initialize list with primary task
        primary_task = DailyTaskItem(
            id="task_primary",
            title=primary_title.strip(),
            is_primary=True,
            completed=False,
            completed_at=None,
        )

        task_list = DailyTaskList(
            user_id=user_id,
            date=date,
            tasks=[primary_task],
            committed=False,
            committed_at=None,
        )

        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc_ref.set(task_list.to_firestore())
            logger.info(f"Initialized daily focus list for user {user_id} on {date}")
            return task_list
        except Exception as e:
            logger.error(f"Error initializing daily tasks: {e}", exc_info=True)
            return task_list

    def add_secondary_task(self, user_id: str, date: str, title: str) -> Tuple[bool, str]:
        """
        Add a secondary task to the list (max 2 secondary tasks, only if uncommitted).
        
        Args:
            user_id: User ID
            date: Date string (YYYY-MM-DD)
            title: Task title
            
        Returns:
            Tuple[bool, message]
        """
        task_list = self.get_daily_tasks(user_id, date)
        if not task_list:
            return False, "Focus list not initialized. Please view your morning brief first."

        if task_list.committed:
            return False, "Focus list is already committed. You cannot add tasks now."

        secondary_tasks = [t for t in task_list.tasks if not t.is_primary]
        if len(secondary_tasks) >= 2:
            return False, "You can add a maximum of 2 secondary tasks to protect your focus."

        task_id = f"task_sec_{len(secondary_tasks) + 1}"
        new_task = DailyTaskItem(
            id=task_id,
            title=title.strip(),
            is_primary=False,
            completed=False,
            completed_at=None,
        )
        task_list.tasks.append(new_task)

        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc_ref.set(task_list.to_firestore())
            return True, "Task added successfully!"
        except Exception as e:
            logger.error(f"Error adding secondary task: {e}", exc_info=True)
            return False, f"Failed to save task: {str(e)}"

    def commit_daily_tasks(self, user_id: str, date: str) -> Tuple[bool, str]:
        """
        Commit the daily tasks, freezing the list.
        
        Args:
            user_id: User ID
            date: Date string (YYYY-MM-DD)
            
        Returns:
            Tuple[bool, message]
        """
        task_list = self.get_daily_tasks(user_id, date)
        if not task_list:
            return False, "Focus list not found."

        if task_list.committed:
            return True, "Focus list is already committed."

        task_list.committed = True
        task_list.committed_at = datetime.utcnow()

        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc_ref.set(task_list.to_firestore())
            logger.info(f"Committed daily focus list for user {user_id} on {date}")
            return True, "Focus list committed! Make it happen today. 💪"
        except Exception as e:
            logger.error(f"Error committing daily tasks: {e}", exc_info=True)
            return False, f"Failed to commit: {str(e)}"

    def toggle_task_completion(
        self, user_id: str, date: str, task_id: str, completed: bool
    ) -> Tuple[bool, Optional[DailyTaskList]]:
        """
        Toggle completion status of a task.
        
        Args:
            user_id: User ID
            date: Date string (YYYY-MM-DD)
            task_id: Task ID to toggle
            completed: True to mark complete, False to uncomplete
            
        Returns:
            Tuple[success, updated_task_list]
        """
        task_list = self.get_daily_tasks(user_id, date)
        if not task_list:
            return False, None

        # Only allow toggling if committed
        if not task_list.committed:
            return False, None

        task_found = False
        for task in task_list.tasks:
            if task.id == task_id:
                task.completed = completed
                task.completed_at = datetime.utcnow() if completed else None
                task_found = True
                break

        if not task_found:
            return False, None

        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc_ref.set(task_list.to_firestore())
            return True, task_list
        except Exception as e:
            logger.error(f"Error toggling task completion: {e}", exc_info=True)
            return False, None


    def save_committed_task_list(
        self,
        user_id: str,
        date: str,
        primary_title: str,
        sec1_title: Optional[str] = None,
        sec2_title: Optional[str] = None,
    ) -> DailyTaskList:
        """
        Create and automatically commit the 3 daily to-dos for tomorrow during check-in.
        
        Args:
            user_id: User ID
            date: Tomorrow's date string (YYYY-MM-DD)
            primary_title: Primary task title (Must-do #1)
            sec1_title: Optional secondary task title #2
            sec2_title: Optional secondary task title #3
            
        Returns:
            DailyTaskList: The committed task list
        """
        tasks: List[DailyTaskItem] = []
        
        # 1. Primary Task
        p_title = primary_title.strip() if primary_title and primary_title.strip() else "Maintain consistency"
        tasks.append(DailyTaskItem(
            id="task_primary",
            title=p_title,
            is_primary=True,
            completed=False,
            completed_at=None,
        ))
        
        # 2. Secondary Task 1
        if sec1_title and sec1_title.strip():
            tasks.append(DailyTaskItem(
                id="task_sec_1",
                title=sec1_title.strip(),
                is_primary=False,
                completed=False,
                completed_at=None,
            ))
            
        # 3. Secondary Task 2
        if sec2_title and sec2_title.strip():
            tasks.append(DailyTaskItem(
                id="task_sec_2",
                title=sec2_title.strip(),
                is_primary=False,
                completed=False,
                completed_at=None,
            ))
            
        task_list = DailyTaskList(
            user_id=user_id,
            date=date,
            tasks=tasks,
            committed=True,
            committed_at=datetime.utcnow(),
        )
        
        try:
            doc_ref = (
                self.firestore.db.collection("daily_tasks")
                .document(user_id)
                .collection("tasks")
                .document(date)
            )
            doc_ref.set(task_list.to_firestore())
            logger.info(f"Saved {len(tasks)} committed to-dos for user {user_id} on {date}")
        except Exception as e:
            logger.error(f"Error saving committed to-dos: {e}", exc_info=True)
            
        return task_list


# Singleton instance
task_service = TaskService()

