"""
Task Management Module for augment-lite-mcp

Provides structured task tracking with:
- Task creation, update, deletion
- Status tracking (pending, in_progress, done, cancelled)
- Priority management
- Parent-child task relationships
- Multi-project support
"""

import sqlite3
import time
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

BASE = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("AUGMENT_DB_DIR", "./data")) / "memory.sqlite"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _resolve_auto_project():
    """Resolve auto project mode intelligently"""
    # Use centralized implementation to avoid code duplication
    from utils.project_utils import resolve_auto_project
    return resolve_auto_project()


def _db():
    """Get database connection and ensure tasks table exists"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        priority INTEGER DEFAULT 0,
        parent_id INTEGER,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        completed_at INTEGER,
        metadata TEXT,
        FOREIGN KEY (parent_id) REFERENCES tasks(id)
    )""")
    
    # Create index for faster queries
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_tasks_project_status 
                    ON tasks(project, status)""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_tasks_parent 
                    ON tasks(parent_id)""")
    
    return conn


class TaskManager:
    """
    Task Manager for structured task tracking.
    
    Supports:
    - CRUD operations on tasks
    - Status transitions (pending → in_progress → done/cancelled)
    - Priority management
    - Parent-child relationships
    - Multi-project isolation
    """
    
    VALID_STATUSES = ["pending", "in_progress", "done", "cancelled"]
    
    def __init__(self, project: str = "auto"):
        """
        Initialize TaskManager.

        Args:
            project: Project name ("auto" for active project, None for global)
        """
        if project == "auto":
            project = _resolve_auto_project()
        self.project = project or ""
    
    def add_task(
        self,
        title: str,
        description: str = "",
        priority: int = 0,
        parent_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a new task.
        
        Args:
            title: Task title (required)
            description: Task description
            priority: Task priority (higher = more important)
            parent_id: Parent task ID (for subtasks)
            metadata: Additional metadata (stored as JSON)
        
        Returns:
            Task ID
        """
        now = int(time.time())
        metadata_json = json.dumps(metadata) if metadata else None
        
        with _db() as conn:
            cursor = conn.execute(
                """INSERT INTO tasks 
                   (project, title, description, status, priority, parent_id, 
                    created_at, updated_at, metadata)
                   VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)""",
                (self.project, title, description, priority, parent_id, now, now, metadata_json)
            )
            return cursor.lastrowid
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task dict or None if not found
        """
        with _db() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE id=? AND project=?",
                (task_id, self.project)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        parent_id: Optional[int] = None,
        include_subtasks: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.
        
        Args:
            status: Filter by status (None for all)
            parent_id: Filter by parent ID (None for root tasks, -1 for all)
            include_subtasks: Include subtasks in results
        
        Returns:
            List of task dicts
        """
        with _db() as conn:
            query = "SELECT * FROM tasks WHERE project=?"
            params = [self.project]
            
            if status:
                query += " AND status=?"
                params.append(status)
            
            if parent_id is not None and parent_id != -1:
                query += " AND parent_id=?"
                params.append(parent_id)
            elif parent_id != -1 and not include_subtasks:
                query += " AND parent_id IS NULL"
            
            query += " ORDER BY priority DESC, created_at ASC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_dict(row) for row in rows]
    
    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a task.
        
        Args:
            task_id: Task ID
            title: New title
            description: New description
            status: New status
            priority: New priority
            metadata: New metadata
        
        Returns:
            True if updated, False if not found
        """
        if status and status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {self.VALID_STATUSES}")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if title is not None:
            updates.append("title=?")
            params.append(title)
        
        if description is not None:
            updates.append("description=?")
            params.append(description)
        
        if status is not None:
            updates.append("status=?")
            params.append(status)
            
            # Set completed_at if status is done
            if status == "done":
                updates.append("completed_at=?")
                params.append(int(time.time()))
        
        if priority is not None:
            updates.append("priority=?")
            params.append(priority)
        
        if metadata is not None:
            updates.append("metadata=?")
            params.append(json.dumps(metadata))
        
        if not updates:
            return False
        
        updates.append("updated_at=?")
        params.append(int(time.time()))
        
        params.extend([task_id, self.project])
        
        with _db() as conn:
            cursor = conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id=? AND project=?",
                params
            )
            return cursor.rowcount > 0
    
    def delete_task(self, task_id: int, delete_subtasks: bool = False) -> bool:
        """
        Delete a task.
        
        Args:
            task_id: Task ID
            delete_subtasks: Also delete all subtasks
        
        Returns:
            True if deleted, False if not found
        """
        with _db() as conn:
            if delete_subtasks:
                # Delete all subtasks recursively
                self._delete_subtasks_recursive(conn, task_id)
            
            cursor = conn.execute(
                "DELETE FROM tasks WHERE id=? AND project=?",
                (task_id, self.project)
            )
            return cursor.rowcount > 0
    
    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """
        Get the current in-progress task (highest priority).
        
        Returns:
            Task dict or None if no in-progress tasks
        """
        tasks = self.list_tasks(status="in_progress")
        return tasks[0] if tasks else None
    
    def resume_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Resume a task (set status to in_progress).
        
        Args:
            task_id: Task ID
        
        Returns:
            Updated task dict or None if not found
        """
        if self.update_task(task_id, status="in_progress"):
            return self.get_task(task_id)
        return None
    
    def get_subtasks(self, parent_id: int) -> List[Dict[str, Any]]:
        """
        Get all subtasks of a parent task.
        
        Args:
            parent_id: Parent task ID
        
        Returns:
            List of subtask dicts
        """
        return self.list_tasks(parent_id=parent_id)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get task statistics.
        
        Returns:
            Dict with counts by status
        """
        with _db() as conn:
            cursor = conn.execute(
                "SELECT status, COUNT(*) FROM tasks WHERE project=? GROUP BY status",
                (self.project,)
            )
            stats = dict(cursor.fetchall())
            
            # Ensure all statuses are present
            for status in self.VALID_STATUSES:
                stats.setdefault(status, 0)
            
            stats["total"] = sum(stats.values())
            return stats
    
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """Convert SQLite row to dict"""
        return {
            "id": row[0],
            "project": row[1],
            "title": row[2],
            "description": row[3],
            "status": row[4],
            "priority": row[5],
            "parent_id": row[6],
            "created_at": row[7],
            "updated_at": row[8],
            "completed_at": row[9],
            "metadata": json.loads(row[10]) if row[10] else None
        }
    
    def _delete_subtasks_recursive(self, conn, parent_id: int):
        """Recursively delete all subtasks"""
        cursor = conn.execute(
            "SELECT id FROM tasks WHERE parent_id=? AND project=?",
            (parent_id, self.project)
        )
        subtask_ids = [row[0] for row in cursor.fetchall()]
        
        for subtask_id in subtask_ids:
            self._delete_subtasks_recursive(conn, subtask_id)
            conn.execute("DELETE FROM tasks WHERE id=?", (subtask_id,))

